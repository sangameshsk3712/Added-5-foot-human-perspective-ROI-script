import cv2
import numpy as np
import socket

# ==================================================
# 🌐 DYNAMIC NETWORK INTEGRATION
# ==================================================
PC_IP = "192.168.29.112"              # Your PC IP address
PORT = 5005                           # Free network port
phone_ip_address = "192.168.29.172"
CAMERA_URL = "http://" + phone_ip_address + ":8080/video"

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cap = cv2.VideoCapture(CAMERA_URL)

if not cap.isOpened():
    print("[FATAL ERROR] Could not establish link to the phone stream.")
    exit()

print("\n==================================================")
print("   5-FOOT PERSPECTIVE MASTER CONTROL ACTIVE       ")
print("==================================================")

last_sent_command = "STOP"

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    height, width, _ = frame.shape
    screen_center_x = int(width / 2)

    # ==================================================
    # 🗼 5-FOOT HEIGHT OPTIMIZATION (REGION OF INTEREST)
    # ==================================================
    # Cut out the top 35% of the screen (ceiling/walls) to prevent false AI triggers
    horizon_cutoff = int(height * 0.35)
    roi_frame = frame[horizon_cutoff:height, 0:width]
    
    # Process only the floor zone inside the HSV matrix
    hsv = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)

    # FIXED CALIBRATION VALUES FOR BRIGHT GREEN 
    lower_green = np.array([35, 50, 50])
    upper_green = np.array([85, 255, 255])

    mask = cv2.inRange(hsv, lower_green, upper_green)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    current_command = "STOP"

    if len(contours) > 0:
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)

        if area > 400: # Threshold adjusted for 5-foot high perspective framing
            ((x, y), radius) = cv2.minEnclosingCircle(largest_contour)
            
            # Map coordinates back to the original full screen scale
            obj_x = int(x)
            obj_y = int(y) + horizon_cutoff

            # Draw AI target overlays
            cv2.circle(frame, (obj_x, obj_y), int(radius), (0, 255, 0), 2)
            cv2.circle(frame, (obj_x, obj_y), 5, (0, 0, 255), -1)

            # High-Perspective Steering Triggers
            if obj_x < (screen_center_x - 90): # Wider tracking buffer zone for stability
                current_command = "LEFT"
            elif obj_x > (screen_center_x + 90):
                current_command = "RIGHT"
            else:
                if radius < 55: 
                    current_command = "FORWARD"
                else:
                    current_command = "STOP"

    # Broadcast movement logic over Wi-Fi
    if current_command != last_sent_command:
        try:
            server_socket.sendto(current_command.encode(), (PC_IP, PORT))
            print(f"[WIFI AIR-BURST] -> Sent Navigation Logic: {current_command}")
            last_sent_command = current_command
        except Exception as e:
            pass

    # Visual Guide Toggles
    cv2.line(frame, (screen_center_x, 0), (screen_center_x, height), (255, 255, 255), 1)
    # Draw a red warning horizontal line showing where the AI starts looking down
    cv2.line(frame, (0, horizon_cutoff), (width, horizon_cutoff), (0, 0, 255), 2)
    cv2.putText(frame, f"AI OUTPUT: {current_command}", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    cv2.imshow("1. 5-Foot Human Perspective View", frame)
    cv2.imshow("2. Floor Level Target Mask", mask)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
server_socket.close()
cv2.destroyAllWindows()
