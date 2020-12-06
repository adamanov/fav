#!/usr/bin/env python
import rospy
import numpy as np
import time
import math as m

from bluerov_sim.msg import ActuatorCommands
from mavros_msgs.srv import CommandBool
from std_msgs.msg import Float64, Float32
from depth_controller.msg import Orientation


from nav_msgs.msg import Odometry
from geometry_msgs.msg import Point
from tf.transformations import euler_from_quaternion, quaternion_from_euler


class Controller():
    def __init__(self, name):
        rospy.init_node(name)
        self.last_depth_time = 0

        rospy.set_param('depth_timeout', 1 * 10**9)

        self.rate = 5

        # self.arm_vehicle()

        self.euler = Orientation()

        rospy.set_param('euler_threshold', 10 * 2*m.pi/360)

        self.depth_setpoint = -0.5
        self.depth = 0.0

        # comming from desired/setpoint topic
        self.thrust_setpoint = 0.0
        # comming from desired/setpoint topic
        self.lateral_thrust_setpoint = 0.0
        # comming from desired/setpoint topic
        self.vertical_thrust_setpoint = 0.0

        self.yaw_setpoint = 0.0       # Desired is 0
        self.pitch_setpoint = 0.0     # Desired is 0
        self.roll_setpoint = 0.0      # Desired is 0

        self.thrust = 0.0
        self.lateral_thrust = 0.0
        self.vertical_thrust = 0.0
        self.yaw_rate = 0.0
        self.pitch_rate = 0.0
        self.roll_rate = 0.0

        self.actuator_pub = rospy.Publisher("mixer/actuator_commands",
                                            ActuatorCommands,
                                            queue_size=1)

        # Need create a desired setpoints Publisher (like depth_setpoint.py for all poses
        #  desired orientation can be also Published)
        print("before Subscriber")

        rospy.Subscriber("depth/state", Float64,
                         self.depth_callback, queue_size=1)

        rospy.Subscriber("desired_pose/setpoint",
                         Point,
                         self.desired_Pose_setpoint_callback,
                         queue_size=1)

        rospy.Subscriber("desired_angle/setpoint",
                         Point,
                         self.desired_Angle_setpoint_callback,
                         queue_size=1)

        # Subscribe to topics to get a current Pose and Orientation
        self.ground_truth_sub = rospy.Subscriber("ground_truth/state", Odometry,
                                                 self.on_ground_truth)

        # For now it commented. We use now a ground truth of state
        """         
        rospy.Subscriber("localization/position_estimate",
                         Point, self.locationPose_callback,
                         queue_size=1)

        """
        # Publish CURRENT POSE / ANGLES to PID Controller
        self.thrust_pub = rospy.Publisher(
            "thrust/state", Float64, queue_size=1)
        self.vt_pub = rospy.Publisher(
            "vertical_thrust/state", Float64, queue_size=1)
        self.lt_pub = rospy.Publisher(
            "lateral_thrust/state", Float64, queue_size=1)

        self.roll_pub = rospy.Publisher("roll/state", Float64, queue_size=1)
        self.pitch_pub = rospy.Publisher("pitch/state", Float64, queue_size=1)
        self.yaw_pub = rospy.Publisher("yaw/state", Float64, queue_size=1)

        # Publish Desired  SETPOINTS
        self.thrust_setpoint_pub = rospy.Publisher(
            "thrust/setpoint", Float64, queue_size=1)
        self.vt_setpoint_pub = rospy.Publisher(
            "vertical_thrust/setpoint", Float64, queue_size=1)
        self.lt_setpoint_pub = rospy.Publisher(
            "lateral_thrust/setpoint", Float64, queue_size=1)

        self.yaw_setpoint_pub = rospy.Publisher(
            "yaw/setpoint", Float64, queue_size=1)
        self.pitch_setpoint_pub = rospy.Publisher(
            "pitch/setpoint", Float64, queue_size=1)
        self.roll_setpoint_pub = rospy.Publisher(
            "roll/setpoint", Float64, queue_size=1)

        # Subscribe to topics of the controller output
        rospy.Subscriber("thrust/control_effort",
                         Float64,
                         self.control_callback_thrust,
                         queue_size=1)
        rospy.Subscriber("vertical_thrust/control_effort",
                         Float64,
                         self.control_callback_vertical_thrust,
                         queue_size=1)
        rospy.Subscriber("lateral_thrust/control_effort",
                         Float64,
                         self.control_callback_lateral_thrust,
                         queue_size=1)
        rospy.Subscriber("yaw/control_effort",
                         Float64,
                         self.control_callback_yaw,
                         queue_size=1)
        rospy.Subscriber("pitch/control_effort",
                         Float64,
                         self.control_callback_pitch,
                         queue_size=1)
        rospy.Subscriber("roll/control_effort",
                         Float64,
                         self.control_callback_roll,
                         queue_size=1)

        rospy.Subscriber("orientation/euler", Orientation,
                         self.orient_callback,
                         queue_size=1)

        # ----- Reading and storing the comming msg. e.g ground_truth (yaw,roll,pitch) , localization (x,y,z)
        # ----- and desired setpoint positions of robot, and after that separate each state and send set into PID
        # ----- controller as a state and setpoint

    def depth_callback(self, msg):
        self.depth = msg.data
    ''' 
    def locationPose_callback(self, msg):
        self.Pose = Point()
        self.Pose.header.stamp = rospy.Time.now()
        # I am not sure about order x y z to thrust /  later thrust / vertical thrust
        self.Pose.x = msg.x  # Thrust
        self.Pose.y = msg.y  # Laterial Thrust
        self.Pose.z = msg.z  # Vertical Thrust

        # Each Pose has to be published individually in order to PID Controller could subscribe

        # Publish current Thrust Position
        self.thrust_msg = Float64()
        self.thrust_msg.data = self.Pose.x
        self.thrust_pub.publish(self.thrust_msg)

        # Publish current Laterial Thrust Position
        self.lt_msg = Float64()
        self.vt_msg.data = self.Pose.y
        self.lt_pub.publish(self.lt_msg)

        # Publish current Vertical Thrust Position
        self.vt_msg = Float64()
        self.vt_msg.data = self.Pose.z
        self.vt_pub.publish(self.vt_msg)
    '''

    def on_ground_truth(self, msg):
        qx = msg.pose.pose.orientation.x
        qy = msg.pose.pose.orientation.y
        qz = msg.pose.pose.orientation.z
        qw = msg.pose.pose.orientation.w

        orientation_list = [qx, qy, qz, qw]
        # Convert Quaternion to Euler angels
        (self.roll, self.pitch, self.yaw) = euler_from_quaternion(orientation_list)
        #print("GT Euler Angles, radian?")
        #print(self.roll, self.pitch, self.yaw)

        self.gt_thrust = msg.pose.pose.position.x           # ground truth thrust
        self.gt_laterial_thrust = msg.pose.pose.position.y  # ground thruth laterial thrust
        self.gt_vertical_thrust = msg.pose.pose.position.z  # ground thruth vertical thrust
        #print("GT Position of robot")
        #print(self.gt_thrust, self.gt_laterial_thrust, self.gt_vertical_thrust)

        # Publish current Roll Angle
        self.roll_msg = Float64()
        self.roll_msg.data = self.roll
        self.roll_pub.publish(self.roll_msg)

        # Publish current Pitch Angle
        self.pitch_msg = Float64()
        self.pitch_msg.data = self.pitch
        self.pitch_pub.publish(self.pitch_msg)

        # Publish current Yaw Angle
        self.yaw_msg = Float64()
        self.yaw_msg = self.yaw
        self.yaw_pub.publish(self.yaw_msg)

        # ---- Temp. will be replaced with localizatio/ground_thruth----
        # Publish current Ground_truth of Thrust
        self.gt_thrust_msg = Float64()
        self.gt_thrust_msg.data = self.gt_thrust
        self.vt_pub.publish(self.gt_thrust_msg)
        # Publish current Ground_truth of Laterial Thrust
        self.gt_laterial_thrust_msg = Float64()
        self.gt_laterial_thrust_msg.data = self.gt_laterial_thrust
        self.lt_pub.publish(self.gt_laterial_thrust_msg)
        # Publsih current Ground_truth of Vertical Thrust
        self.gt_vertical_thrust_msg = Float64()
        self.gt_vertical_thrust_msg.data = self.gt_vertical_thrust
        self.vt_pub.publish(self.gt_vertical_thrust_msg)

       # Each Angle has to be published individually in order to PID Controller could subscribe

    def desired_Pose_setpoint_callback(self, msg):
        self.thrust_setpoint = msg.x
        self.lateral_thrust_setpoint = msg.y
        self.vertical_thrust_setpoint = msg.z

        # Each Pose Setpoint has to be published individually in order to PID Controller could subscribe

        # Publish setpoints Thrust Position for a controller
        self.s_thrust_msg = Float64()
        self.s_thrust_msg.data = self.thrust_setpoint
        self.thrust_setpoint_pub.publish(self.s_thrust_msg)
        # Publish setpoints Vertical Thrust Position for a controller
        self.s_vt_msg = Float64()
        self.s_vt_msg = self.vertical_thrust_setpoint
        self.vt_setpoint_pub.publish(self.s_vt_msg)
        # Publish setpoints laterial Position for a controller
        self.s_lt_msg = Float64()
        self.s_lt_msg = self.lateral_thrust_setpoint
        self.lt_setpoint_pub.publish(self.s_lt_msg)

    def desired_Angle_setpoint_callback(self, msg):
        self.roll_setpoint = msg.x
        self.pitch_setpoint = msg.y
        self.yaw_setpoint = msg.z   # worked

        # Publish setpoints Yaw Angle for a controller
        self.s_yaw_msg = Float64()
        self.s_yaw_msg = self.yaw_setpoint
        self.yaw_setpoint_pub.publish(self.s_yaw_msg)
        # Publish setpoints Pitch Angle for a controller

        self.s_pitch_msg = Float64()
        self.s_pitch_msg = self.pitch_setpoint
        self.pitch_setpoint_pub.publish(self.s_pitch_msg)

        # Publish setpoints Roll Angle for a controller
        self.s_roll_msg = Float64()
        self.s_roll_msg = self.roll_setpoint
        self.roll_setpoint_pub.publish(self.s_roll_msg)

        # --- PID Controller required things are done

    def orient_callback(self, msg):
        self.euler = msg

    def isStable(self):
        return (rospy.get_param('euler_threshold') > max(abs(self.euler.roll), abs(self.euler.pitch)))

    """ def arm_vehicle(self):
        rospy.wait_for_service("mavros/cmd/arming")
        arm = rospy.ServiceProxy("mavros/cmd/arming", CommandBool)
        while not arm(True).success:
            rospy.logwarn_throttle(1, "Could not arm vehicle. Keep trying.")
        rospy.loginfo("Armed successfully.")

    def disarm_vehicle(self):
        rospy.wait_for_service("mavros/cmd/arming")
        arm = rospy.ServiceProxy("mavros/cmd/arming", CommandBool)
        arm(False) """

    # ------------------------control_callback_vertical_thrust-------------------------------------------------------
    def control_callback_vertical_thrust(self, msg):
        # print(msg.data)
        self.control_effort_vertical_thrust = msg.data

        safezone_upper = rospy.get_param('safezone_upper')
        safezone_lower = rospy.get_param('safezone_lower')
        # print("setpoint: " + str(self.depth_setpoint) + "   depth: " + str(self.depth) + "  Control_effort: " + str(self.control_effort))
        isNotTimedout = rospy.get_param(
            'depth_timeout') > rospy.Time.now().nsecs - self.last_depth_time
        if (isNotTimedout and self.isStable()):
            if (self.depth < safezone_upper and self.depth > safezone_lower):
                # Congratulations You passed ALL CHECKS !!!
                self.set_vertical_thrust(self.control_effort_vertical_thrust)
            elif self.depth > safezone_upper:
                self.set_vertical_thrust(
                    min(self.control_effort_vertical_thrust, 0))
                rospy.loginfo(
                    "over safezone_upper!!   (No positive control_effort allowed)")
            elif self.depth < safezone_lower:
                self.set_vertical_thrust(max(self.control_effort, 0))
                rospy.loginfo(
                    "under safezone_lower!!   (No negative control_effort allowed)")
            else:
                self.set_vertical_thrust(0.0)
                rospy.loginfo(
                    "WARNING: Numerical Problems??? control_effort is 0!")
        elif isNotTimedout:
            self.set_vertical_thrust(0.0)
            rospy.loginfo("Wet whale is tilted!")
            rospy.loginfo("(You could change 'euler_threshold')")
        elif self.isStable():
            self.set_vertical_thrust(0.0)
            rospy.loginfo("No depth data recieved in the last sec! ")
            rospy.loginfo("(You could change 'depth_timeout')")
        else:
            self.set_vertical_thrust(0.0)
            rospy.loginfo(
                "Wet whale is tilted over and didn't recieved any depth data !")
            rospy.loginfo(
                "(You could change 'depth_timeout' and 'euler_threshold')")

    def control_callback_thrust(self, msg):
        # print(msg.data)
        self.control_effort_thrust = msg.data

    def control_callback_lateral_thrust(self, msg):
        # print(msg.data)
        self.control_effort_lateral_thrust = msg.data

    def control_callback_yaw(self, msg):
        # print(msg.data)
        self.control_effort_yaw = msg.data

    def control_callback_pitch(self, msg):
        # print(msg.data)
        self.control_effort_pitch = msg.data

    def control_callback_roll(self, msg):
        # print(msg.data)
        self.control_effort_roll = msg.data

    # Set controller state, and send after that to mixer/actuator_commands, after that
    # that node will re orginize thet data and publsih to motor

    def set_thrust(self, value):
        self.thrust = max(-1, min(1, value))

    def set_yaw_rate(self, value):
        self.yaw_rate = max(-1, min(1, value))

    def set_vertical_thrust(self, value):
        self.vertical_thrust = max(-1, min(1, value))

    def set_lateral_thrust(self, value):
        self.lateral_thrust = max(-1, min(1, value))

    def set_pitch_rate(self, value):
        self.pitch_rate = max(-1, min(1, value))

    def set_roll_rate(self, value):
        self.roll_rate = max(-1, min(1, value))

    def publish_message(self):
        msg = ActuatorCommands()
        msg.header.stamp = rospy.Time.now()
        msg.thrust = self.thrust
        msg.yaw = self.yaw_rate
        msg.lateral_thrust = self.lateral_thrust
        msg.vertical_thrust = self.vertical_thrust
        msg.pitch = self.pitch_rate
        msg.roll = self.roll_rate
        self.actuator_pub.publish(msg)

    def run(self):
        # rospy.spin()
        rate = rospy.Rate(self.rate)
        while not rospy.is_shutdown():
            self.publish_message()
            rate.sleep()


def main():
    print("ENTER TO THE CONTROLLER CLASS")
    node = Controller("main_controller")
    node.run()


if __name__ == "__main__":
    main()
