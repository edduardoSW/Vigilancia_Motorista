import cv2
import time
import threading
import winsound
import requests

class SimpleDriverMonitor:
    def __init__(self):
        print("📷 Carregando detectores básicos...")

        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

        self.eyes_closed_start_time = None
        self.is_alerting = False
        self.alert_sent = False
        self.last_alert_time = 0

        print("✅ Sistema pronto!")

    def play_alert_sound(self):
        if not self.is_alerting:
            self.is_alerting = True
            print("🔊 ALERTA DE SIRENE!")

            def alert():
                try:
                    for _ in range(5):
                        winsound.Beep(2000, 150)
                        time.sleep(0.05)
                        winsound.Beep(1000, 150)
                        time.sleep(0.05)
                finally:
                    self.is_alerting = False

            threading.Thread(target=alert, daemon=True).start()

    def send_alert_to_web(self, duration):
        try:
            alert_data = {
                "driver_id": 1,
                "vehicle_id": 1,
                "alert_type": "possivel_sonolencia",
                "duration": round(duration, 2),
                "risk_level": 3
            }
            response = requests.post(
                "http://localhost:8000/api/alerts",
                json=alert_data,
                timeout=2
            )
            if response.status_code in [200, 201]:
                print("✅ Alerta enviado para página web!")
        except Exception as e:
            print(f"⚠️ Falha ao enviar para página web (servidor offline?): {e}")

    def process_frame(self, frame):
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(100, 100)
            )

            face_detected = len(faces) > 0
            eyes_detected = False
            eyes = []

            if face_detected:
                (x, y, w, h) = faces[0]
                roi_gray = gray[y:y+h, x:x+w]

                eyes = self.eye_cascade.detectMultiScale(
                    roi_gray,
                    scaleFactor=1.1,
                    minNeighbors=3,
                    minSize=(30, 30)
                )

                eyes_detected = len(eyes) >= 2

            is_sleepy = False
            time_closed = 0

            if face_detected and not eyes_detected:
                if self.eyes_closed_start_time is None:
                    self.eyes_closed_start_time = time.time()

                time_closed = time.time() - self.eyes_closed_start_time

                if time_closed > 2.0:
                    is_sleepy = True
                    if not self.alert_sent:
                        self.play_alert_sound()
                        self.send_alert_to_web(time_closed)
                        self.alert_sent = True
                        self.last_alert_time = time.time()
                    else:
                        current_time = time.time()
                        if current_time - self.last_alert_time > 0.30 and not self.is_alerting:
                            self.play_alert_sound()
                            self.last_alert_time = current_time
            else:
                if self.eyes_closed_start_time is not None:
                    closed_duration = time.time() - self.eyes_closed_start_time
                    if closed_duration > 0.2:
                        print(f"👁️ Piscada: {closed_duration:.2f}s")
                self.eyes_closed_start_time = None
                self.alert_sent = False

            display = frame.copy()

            if face_detected:
                (x, y, w, h) = faces[0]
                cv2.rectangle(display, (x, y), (x+w, y+h), (0, 255, 0), 3)
                cv2.putText(display, "ROSTO", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                for (ex, ey, ew, eh) in eyes:
                    cv2.rectangle(display, (x+ex, y+ey), (x+ex+ew, y+ey+eh), (0, 255, 255), 2)

            if is_sleepy:
                status_text = "POSSIVEL SONO!"
                color = (0, 0, 255)
            elif face_detected and not eyes_detected:
                status_text = "OLHOS FECHADOS"
                color = (0, 165, 255)
            elif face_detected:
                status_text = "ACORDADO"
                color = (0, 255, 0)
            else:
                status_text = "ROSTO NAO ENCONTRADO"
                color = (128, 128, 128)

            cv2.putText(display, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)

            if self.eyes_closed_start_time is not None:
                time_closed = time.time() - self.eyes_closed_start_time
                cv2.putText(display, f"Tempo: {time_closed:.1f}s", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            h, w = display.shape[:2]
            cv2.putText(display, "Pressione 'q' para sair", (10, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 2)

            return display, is_sleepy

        except Exception as e:
            print(f"⚠️ Erro: {e}")
            return frame, False

    def start(self, camera_id=0):
        print("🎥 Abrindo câmera...")
        print("📍 Certifique-se que o servidor web está rodando (uvicorn backend.main:app --reload)")
        print("🌐 Página web: http://localhost:8000")
        cap = cv2.VideoCapture(camera_id)

        if not cap.isOpened():
            print("❌ Erro ao abrir a câmera!")
            return

        print("✅ Câmera aberta! Iniciando monitoramento...")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Falha na câmera")
                time.sleep(0.1)
                continue

            try:
                display, sleepy = self.process_frame(frame)
                cv2.imshow("DriveSafe AI - Monitoramento", display)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except Exception as e:
                print(f"⚠️ Erro no loop: {e}")
                time.sleep(0.1)
                continue

        cap.release()
        cv2.destroyAllWindows()
        print("✅ Monitoramento finalizado!")

if __name__ == "__main__":
    monitor = SimpleDriverMonitor()
    monitor.start()
