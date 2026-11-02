import rclpy
import json
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
from ultralytics import YOLO
import cv2

class YoloNode(Node):
    def __init__(self):
        super().__init__('yolo_node')
        self.bridge = CvBridge()

        self.subscription = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )
        self.publisher = self.create_publisher(Image, '/yolo/annotated_image', 10)
        self.detection_pub = self.create_publisher(String, '/yolo/detections', 10)
        self.model = YOLO("yolov8m.pt")

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self.get_logger().info(f"received frame shape: {frame.shape}")

        results = self.model(frame)
        detections = []

        # Process all detections first
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                if conf < 0.5:
                    continue

                detections.append({
                    "class": self.model.names[cls],
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2]
                })

                self.get_logger().info(
                    f"Detected {self.model.names[cls]} confidence: ({conf:.2f}) at {x1,y1,x2,y2}"
                )

                # Draw bounding box + label
                label = f"{self.model.names[cls]} {conf:.2f}"

                if conf > 0.7:
                    color = (0, 255, 0)     # green
                else:
                    color = (0, 255, 255)   # yellow

                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.putText(frame, label, (int(x1), int(y1) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        
        annotated_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        self.publisher.publish(annotated_msg)

        # Publish detections JSON once per frame
        msg = String()
        msg.data = json.dumps(detections)
        self.detection_pub.publish(msg)




        




def main(args=None):
    rclpy.init(args=args)
    node = YoloNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

