import rclpy
import math
from rclpy.node import Node
from std_msgs.msg import String
import json
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from geometry_msgs.msg import Twist


class BehaviourControllerNode(Node):
    def __init__(self):
        super().__init__('behaviour_controller_node')

        # Navigation client
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.yolo_sub = self.create_subscription(
            String,
            '/yolo/detections',
            self.yolo_callback,
            10
        )
        
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        # Subscribe to LLM output
        self.subscription = self.create_subscription(
            String,
            'robot_tasks',
            self.task_callback,
            10
        )

        self.get_logger().info("Behaviour Controller initialised and ready")
        self.busy = False 

    def task_callback(self, msg):
        if self.busy:
            self.get_logger().info("Currently busy, ignoring new task")
            return

        try:
            data = json.loads(msg.data)
        except Exception as e:
            self.get_logger().error(f"Failed to parse JSON: {e}")
            return

        tasks = data.get("tasks", [])

        if not isinstance(tasks, list) or len(tasks) == 0:
            self.get_logger().error("No valid tasks found in message")
            return

        # Store ALL tasks so we can run them sequentially
        self.task_queue = tasks

        # Start the first task
        self.start_next_task()

    def handle_task(self, action, location, obj):
        if action == "navigate":
            self.get_logger().info(f"Navigating to {location}")
            self.navigate_to(location)

        elif action == "search":
            self.get_logger().info(f"Searching for {obj} in {location}")
            self.search_for_object(obj, location)

        elif action == "stop":
            self.get_logger().info("Stopping robot")
            self.stop_robot()

    def start_next_task(self):
        if not self.task_queue:
            self.get_logger().info("All tasks completed")
            self.busy = False

            #reset so next command starts fresh 
            if hasattr(self, "search_target"):
                del self.search_target
            
            if hasattr(self, "search_timer"):
                try:
                    self.search_timer.cancel()
                except:
                    pass
                del self.search_timer
                
            if hasattr(self, 'nav_goal_handle'):
                del self.nav_goal_handle

            

            return

        task = self.task_queue.pop(0)

        action = task.get("action")
        location = task.get("target_location")
        obj = task.get("target_object")

        self.get_logger().info(f"Starting task: {action}, {obj}, at {location}")

        self.busy = True
        self.handle_task(action, location, obj)

    def navigate_to(self, location):
        pose = self.location_to_pose(location)
        if pose is None:
            self.get_logger().error(f"Invalid location: {location}")
            return

        goal = NavigateToPose.Goal()
        goal.pose = pose

        self.nav_client.wait_for_server()
        future = self.nav_client.send_goal_async(goal)
        future.add_done_callback(self.goal_response_callback)  

    def navigation_done(self, future):
        result = future.result()

        if result.status != 4:  # SUCCEEDED
            self.get_logger().warn(f"Navigation failed with status {result.status}")
            self.busy = False
            self.start_next_task()
            return

        self.get_logger().info("Navigation completed")

        self.busy = False
        self.start_next_task()  # Start the next task in the queue

    def goal_response_callback(self, future):
        self.nav_goal_handle = future.result()
        if not self.nav_goal_handle.accepted:
            self.get_logger().info("Goal rejected")
            return

        self.get_logger().info("Goal accepted, waiting for result")
        result_future = self.nav_goal_handle.get_result_async()
        result_future.add_done_callback(self.navigation_done)


    def location_to_pose(self, location):
        locations = {
            "top_left_room": (-5.6, -1.57, 0.0),
            "bottom_right_room": (6.81, -6.01, 0.0),
            "middle_room": (-1.79, -3.56, 0.0),
            "bottom_left_room": (-5.47, -4.24, 0.0),
            "top_right_room": (5.74, -3.30, 0.0),
            "trash_room": (1.89, -1.49, 0.0),
        }

        if location not in locations:
            return None

        x, y, yaw = locations[location]
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        return pose

    def search_for_object(self, obj, location):
        self.get_logger().info(f"Searching for {obj} in {location}")
        self.search_target = obj.lower().strip()  # Normalize target object name
        self.search_timer = self.create_timer(0.2, self.scan_step)
        

    def scan_step(self):
        # Keep rotating slowly
        self.rotate_robot(0.25)

            
    def yolo_callback(self, msg):
        try:
            detections = json.loads(msg.data)
        except:
            return

        # If we are not searching, ignore detections
        if not hasattr(self, "search_target"):
            return

        target = self.search_target.lower().strip()

        for det in detections:
            det_class = det.get("class", "").lower().strip()

            if target in det_class:
                self.get_logger().info(f"FOUND {self.search_target} (via YOLO callback)!")
                self.stop_robot()

                # Stop scanning timer if active
                if hasattr(self, "search_timer"):
                    self.search_timer.cancel()

                del self.search_target

                self.busy = False
                self.start_next_task()
                return

    def rotate_robot(self, speed=0.3):
        twist = Twist()
        twist.angular.z = speed
        self.cmd_vel_pub.publish(twist)

    def stop_robot(self):
            # Cancel Nav2 goal if active
        if hasattr(self, 'nav_goal_handle'):
            try:
                self.nav_goal_handle.cancel_goal_async()
            except:
                pass

        # Publish zero velocity
        twist = Twist()
        self.cmd_vel_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = BehaviourControllerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()