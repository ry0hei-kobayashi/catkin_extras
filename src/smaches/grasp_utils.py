# -*- coding: utf-8 -*-
import cv2 
import tf as tf
import tf2_ros as tf2
import rospy
import numpy as np
import ros_numpy
from std_msgs.msg import String
from tmc_msgs.msg import Voice
from geometry_msgs.msg import Twist, WrenchStamped, TransformStamped, Pose
from sensor_msgs.msg import Image as ImageMsg, PointCloud2
import tmc_control_msgs.msg
import trajectory_msgs.msg

#import math as m
#import moveit_commander
#import moveit_msgs.msg

#Class to get XTION camera info (head)
class RGBD():
    def __init__(self):
        self._br = tf.TransformBroadcaster()
        self._cloud_sub = rospy.Subscriber(
            "/hsrb/head_rgbd_sensor/depth_registered/rectified_points",
            PointCloud2, self._cloud_cb)
        self._points_data = None
        self._image_data = None
        self._h_image = None
        self._region = None
        self._h_min = 0
        self._h_max = 0
        self._xyz = [0, 0, 0]
        self._frame_name = None

    def _cloud_cb(self, msg):
        self._points_data = ros_numpy.numpify(msg)
        self._image_data = \
        self._points_data['rgb'].view((np.uint8, 4))[..., [2, 1, 0]]
        hsv_image = cv2.cvtColor(self._image_data, cv2.COLOR_RGB2HSV_FULL)
        self._h_image = hsv_image[..., 0]
        self._region = \
        (self._h_image > self._h_min) & (self._h_image < self._h_max)
        if not np.any(self._region):
            return
            
        (y_idx, x_idx) = np.where(self._region)
        x = np.average(self._points_data['x'][y_idx, x_idx])
        y = np.average(self._points_data['y'][y_idx, x_idx])
        z = np.average(self._points_data['z'][y_idx, x_idx])
        self._xyz = [y, x, z]
        if self._frame_name is None:
            return

        self._br.sendTransform(
        (x, y, z), tf.transformations.quaternion_from_euler(0, 0, 0),
        rospy.Time(msg.header.stamp.secs, msg.header.stamp.nsecs),
        self._frame_name,
        msg.header.frame_id)

    def get_image(self):
        return self._image_data

    def get_points(self):
        return self._points_data

    def get_h_image(self):
        return self._h_image

    def get_region(self):
        return self._region

    def get_xyz(self):
        return self._xyz

    def set_h(self, h_min, h_max):
        self._h_min = h_min
        self._h_max = h_max

    def set_coordinate_name(self, name):
        self._frame_name = name
        
#Color segmentator
    def color_segmentator(self, color = "orange"):
        image = self.get_image()
        if(color == "blue"):
            lower_threshold = (100,120,100)
            upper_threshold = (150,220,240)
        else:
            lower_threshold = (102,95,97)
            upper_threshold = (115,255,255)
        img_hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        mask = cv2.inRange(img_hsv, lower_threshold, upper_threshold)
        res = cv2.bitwise_and(img_hsv, img_hsv, mask=mask)
        pos = []
        pixels = cv2.findNonZero(mask)
        pixels = list(cv2.mean(pixels))
        pos.append(pixels[:2])
        return pos

#Class to get hand camera images(RGB)
class HAND_RGB():
    def __init__(self):
        self.cam_sub = rospy.Subscriber(
            '/hsrb/hand_camera/image_raw',
            ImageMsg, self._callback)
        self._points_data = None
        self._image_data = None
        
    def _callback(self, msg):
        self._image_data = ros_numpy.numpify(msg)
        
    def get_image(self):
        image = self._image_data
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return image
    
#Color segmentator
    def color_segmentator(self, color = "orange"):
        image = self.get_image()
        if(color == "blue"):
            lower_threshold = (100,120,100)
            upper_threshold = (150,220,240)
        else:
            # lower_threshold = (102,95,97)
            # upper_threshold = (115,255,255)
            lower_threshold = (105,130,100)
            upper_threshold = (115,225,255)
        img_hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        mask = cv2.inRange(img_hsv, lower_threshold, upper_threshold)
        res = cv2.bitwise_and(img_hsv, img_hsv, mask=mask)
        pos = []
        pixels = cv2.findNonZero(mask)
        pixels = list(cv2.mean(pixels))
        pos.append(pixels[:2])
        return pos


#Class to get wrist sensor info (Force and torque)
class WRIST_SENSOR():
    def __init__(self):
        self._cam_sub = rospy.Subscriber(
            '/hsrb/wrist_wrench/compensated',
            WrenchStamped, self._callback)
        self.force = None
        self.torque = None
         
    def _callback(self, msg):
        self.force = msg.wrench.force
        self.torque = msg.wrench.torque

    def get_force(self):
        force = [self.force.x, self.force.y, self.force.z]
        return force
    
    def get_torque(self):
        torque = [self.torque.x, self.torque.y, self.torque.z]
        return torque

#Class to handle end effector (gripper)
class GRIPPER():
    def __init__(self):
        self._grip_cmd_pub = rospy.Publisher('/hsrb/gripper_controller/command',
                               trajectory_msgs.msg.JointTrajectory, queue_size=100)
        self._grip_cmd_force = rospy.Publisher('/hsrb/gripper_controller/grasp/goal',
        			tmc_control_msgs.msg.GripperApplyEffortActionGoal, queue_size=100)
        			
        self._joint_name = "hand_motor_joint"
        self._position = 0.5
        self._velocity = 0.5
        self._effort = 0.0
        self._duration = 1

    def _manipulate_gripper(self):
        traj = trajectory_msgs.msg.JointTrajectory()
        traj.joint_names = [self._joint_name]
        p = trajectory_msgs.msg.JointTrajectoryPoint()
        p.positions = [self._position]
        p.velocities = [self._velocity]
        p.accelerations = []
        p.effort = [self._effort]
        p.time_from_start = rospy.Duration(self._duration)
        traj.points = [p]
        self._grip_cmd_pub.publish(traj)
        
    def _apply_force(self):
        app_force = tmc_control_msgs.msg.GripperApplyEffortActionGoal()
        app_force.goal.effort = -0.5
        self._grip_cmd_force.publish(app_force)
        
    def change_velocity(self, newVel):
        self._velocity = newVel
    
    def open(self):
        self._position = 1.23
        self._effort = 0
        self._manipulate_gripper()

    def steady(self):
        self._position = 0.2
        self._effort = -0.3
        self._manipulate_gripper()
        
    def close(self):
        self._position = 0.0
        self._effort = 0.3
        # self._manipulate_gripper()
        self._apply_force()
        rospy.sleep(0.8)

class OMNIBASE():
    def __init__(self):
        self._base_vel_pub = rospy.Publisher('/hsrb/command_velocity', Twist, queue_size=10)
        self.velX = 0
        self.velY = 0
        self.velT = 0
        self.timeout = 0.5
        self.MAX_VEL = 0.03
        self.MAX_VEL_THETA = 0.5
    def _move_base_vel(self):
            twist = Twist()
            twist.linear.x = self.velX
            twist.linear.y = self.velY
            twist.angular.z = self.velT
            self._base_vel_pub.publish(twist)

    def _move_base_time(self):
            start_time = rospy.Time.now().to_sec()
            while rospy.Time.now().to_sec() - start_time < self.timeout:  
                self._move_base_vel()

    def tiny_move(self, velX = 0, velY = 0, velT = 0, std_time = 0.5, MAX_VEL = 0.03, MAX_VEL_THETA = 0.5):
        self.MAX_VEL = MAX_VEL
        self.MAX_VEL_THETA = MAX_VEL_THETA
        self.timeout = std_time
        if abs(velX) > MAX_VEL: 
            self.velX =  MAX_VEL * (velX / abs(velX))
        else:
            self.velX = velX
        if abs(velY) > MAX_VEL:
            self.velY = MAX_VEL * (velY / abs(velY))
        else:
            self.velY = velY
        if abs(velT) > MAX_VEL_THETA:
            self.velT = MAX_VEL_THETA * (velT / abs(velT))
        else:
            self.velT = velT
        self._move_base_time()

class GAZE():
    def __init__(self):
        self._x = 0
        self._y = 0
        self._z = 0
        self._reference = 'map'
        self._cam = 'head_rgbd_sensor_link'
        self._base = 'base_link'
        self._hand = 'hand_palm_link'
        self._tf_man = TF_MANAGER()
    def _gaze_point(self):
    ###Moves head to make center point of rgbd image to coordinates w.r.t.map
        # traf1 = self._tfbuff.lookup_transform(self._reference, self._cam, rospy.Time(0))
        # rospy.sleep(0.5)
        # traf2 = selftfbuff.lookup_transform(self._reference, self._base, rospy.Time(0)) 
        # trans,_ = tf2_obj_2_arr(traf1)
        # _, rot = tf2_obj_2_arr(traf2)


        trans, dc = self._tf_man.getTF(ref_frame=self._reference,target_frame=self._cam)
        rospy.sleep(0.3)
        dc,rot = self._tf_man.getTF(ref_frame=self._reference, target_frame=self._base)

        # trans,dc = self._tf_man.tf2_obj_2_arr(transformation1)
        # dc,rot = self._tf_man.tf2_obj_2_arr(transformation2)

        e = tf.transformations.euler_from_quaternion(rot)

        x_rob, y_rob, z_rob, th_rob = trans[0], trans[1], trans[2], e[2]

        D_x = x_rob - self._x
        D_y = y_rob - self._y
        D_z = z_rob - self._z
        D_th = np.arctan2(D_y,D_x)
        pan_correct = (- th_rob + D_th + np.pi) % (2*np.pi)
        if(pan_correct > np.pi):
            pan_correct -= 2*np.pi
        if(pan_correct < -np.pi):
            pan_correct += 2*np.pi

        if ((pan_correct) > .5 * np.pi):
            print ('Exorcist alert')
            pan_correct=.5*np.pi
        head_pose = [0,0]
        head_pose[0] = pan_correct
        tilt_correct = np.arctan2(D_z,np.linalg.norm((D_x,D_y)))
        head_pose [1] = -tilt_correct
        return head_pose
    
    def absolute(self, x, y, z):
        self._x = x
        self._y = y
        self._z = z
        self._reference = 'map'
        return self._gaze_point()
    def relative(self, x, y, z):
        self._x = x
        self._y = y
        self._z = z
        self._reference = 'base_link'
        return self._gaze_point()
    def hand(self, x, y, z):
        self._x = x
        self._y = y
        self._z = z
        self._reference = 'base_link'

# Funciones aisladas

    
    
class TF_MANAGER():
    def __init__(self):
        self._tfbuff = tf2.Buffer()
        self._lis = tf2.TransformListener(self._tfbuff)
        self._tf_static_broad = tf2.StaticTransformBroadcaster()
        self._broad = tf2.TransformBroadcaster()

    def _fillMsg(self, pos = [0,0,0], rot = [0,0,0,1] ,point_name ='', ref="map"):
        TS = TransformStamped()
        TS.header.stamp = rospy.Time.now()
        TS.header.frame_id = ref
        TS.child_frame_id = point_name
        TS.transform.translation.x = pos[0]
        TS.transform.translation.y = pos[1]
        TS.transform.translation.z = pos[2]
        TS.transform.rotation.x = rot[0]
        TS.transform.rotation.y = rot[1]
        TS.transform.rotation.z = rot[2]
        TS.transform.rotation.w = rot[3]
        return TS

    def pub_tf(self, pos = [0,0,0], rot = [0,0,0,1] ,point_name ='', ref="map"):
        dinamic_ts = self._fillMsg(pos, rot, point_name, ref)
        self._broad.sendTransform(dinamic_ts)

    def pub_static_tf(self, pos = [0,0,0], rot = [0,0,0,1] ,point_name ='', ref="map"):
        static_ts = self._fillMsg(pos, rot, point_name, ref)
        self._tf_static_broad.sendTransform(static_ts)

    def change_ref_frame_tf(self, point_name = '', new_frame = 'map'):
        try:
            traf = self._tfbuff.lookup_transform(new_frame, point_name, rospy.Time(0))
            translation, rotational = self.tf2_obj_2_arr(traf)
            self.pub_static_tf(pos = translation, rot = rotational, point_name = point_name, ref = new_frame)
            return True
        except:
            return False

    def getTF(self, target_frame='', ref_frame='map'):
        try:
            tf = self._tfbuff.lookup_transform(ref_frame, target_frame, rospy.Time(0))
            return self.tf2_obj_2_arr(tf)
        except:
            return [False,False]

    def tf2_obj_2_arr(self, transf):
        pos = []
        pos.append(transf.transform.translation.x)
        pos.append(transf.transform.translation.y)
        pos.append(transf.transform.translation.z)
    
        rot = []
        rot.append(transf.transform.rotation.x)
        rot.append(transf.transform.rotation.y)
        rot.append(transf.transform.rotation.z)
        rot.append(transf.transform.rotation.w)

        return [pos, rot]

def talk(msg):
    talker = rospy.Publisher('/talk_request', Voice, queue_size=10)
    voice = Voice()
    voice.language = 1
    voice.sentence = msg
    talker.publish(voice)
def set_pose_goal(pos=[0,0,0], rot=[0,0,0,1]):
    pose_goal = Pose()
    pose_goal.orientation.x = rot[0]
    pose_goal.orientation.y = rot[1]
    pose_goal.orientation.z = rot[2]
    pose_goal.orientation.w = rot[3]
    pose_goal.position.x = pos[0]
    pose_goal.position.y = pos[1]
    pose_goal.position.z = pos[2]
    return pose_goal