from google import genai
import json
import re
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class LanguageModel(Node):
    def __init__(self):
        super().__init__('language_model')

        # Gemini client
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY")) # provide your Gemini API key as an environment variable
        self.model = "gemini-2.5-flash"
        #self.model = "gemini-3-flash-preview" #for testing different models

        # Publisher to behaviour controller
        self.publisher = self.create_publisher(String, 'robot_tasks', 10)

        self.get_logger().info("Language Model ready")

    def process_input(self, user_input):
        task_dict = self.JSON_Encode("", user_input)

        msg = String()
        msg.data = json.dumps(task_dict)
        self.publisher.publish(msg)

        self.get_logger().info(f"Published: {msg.data}")

    def JSON_Encode(self, prompt, user_text):
        prompt = f"""
        Convert the following user input into JSON using this schema:
        {{
            "tasks": [
                {{
                    "action": "<action>",
                    "target_location": "<location>",
                    "target_object": "<object>"
                }}
            ]
        }}

        Rules:
        - JSON only.
        - No markdown.
        - Use only these actions: navigate, search, pick_up, place, follow, stop.
        - Use only these locations: top_left_room, bottom_left_room, central_room, trash_room, bottom_right_room, top_right_room.

        User instruction: "{user_text}"
        """
        #this is for evaluating latency
        start_time = time.time()

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )

        latency = round(time.time() - start_time, 3)
        raw = response.candidates[0].content.parts[0].text
        cleaned = re.sub(r"```json|```", "", raw).strip()
        #ends timing here
        print(f"\n--- RESULT ---")
        print(f"Model:    {self.model}")
        print(f"Input:    {user_text}")
        print(f"Latency:  {latency}s")
        print(f"Output:   {json.dumps(json.loads(cleaned), indent=2)}")
        print(f"--------------\n")

        
        return json.loads(cleaned)


def main(args=None):
    rclpy.init(args=args)
    node = LanguageModel()

    # Clean input loop — no timer, no early publish
    while rclpy.ok():
        user_input = input("Enter command: ")
        node.process_input(user_input)
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_node()
    rclpy.shutdown()
