import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist

class Avoider(Node):
    def __init__(self):
        super().__init__('avoider')
        self.sub = self.create_subscription(LaserScan, '/scan', self.callback, 10)
        self.pub = self.create_publisher(Twist, '/cmd_vel_nav', 10)


    def detect(self, msg):
        #find object direclty infront using middle ray
        ranges = msg.ranges #array of all rays
        mid = len(ranges)//2
        front_distance = ranges[mid]
        right_side = ranges[:mid]
        left_side = ranges[mid:]
        right_min = min(right_side)
        left_min = min(left_side)


        if front_distance <= 0.7:
            #object detected 
            if left_min > right_min:
                self.avoid("left")
            else:
                #turn right
                self.avoid("right")
        

    def callback(self, msg):
        # This runs automatically every time new LIDAR data arrives
        self.detect(msg)

    def avoid(self, direction):
        cmd = Twist()
        cmd.linear.x = 0.0
        if direction == "left":
            cmd.angular.z =0.5
        elif direction == "right":
            cmd.angular.z= -0.5
        self.pub.publish(cmd)





def main(args=None):
    rclpy.init(args=args)
    node = Avoider()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()


