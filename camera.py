import cv2

def capture_photo(filename):
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("Camera not opened")
        return False

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        cv2.imshow("Press S to Save | Q to Quit", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            cv2.imwrite(filename, frame)
            break
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return True
