#! /usr/bin/env python3

import tf
import tf2_ros
import numpy as np
import rospy
import actionlib
from hmm_navigation.msg import NavigateAction ,NavigateActionGoal,NavigateActionFeedback,NavigateActionResult
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist, PointStamped
from visualization_msgs.msg import Marker , MarkerArray

##################################################
def pose2feedback(pose_robot,quat_robot):
    feed = NavigateActionFeedback()
    feed.feedback.x_robot   = pose_robot[0]
    feed.feedback.y_robot   = pose_robot[1]
    euler= tf.transformations.euler_from_quaternion((quat_robot[0] ,quat_robot[1] ,quat_robot[2] ,quat_robot[3] )) 
    feed.feedback.yaw_robot = euler[2]
    feed.feedback.status    = 3
    return feed
class HMM_navServer():

    def __init__(self):
        self.hmm_nav_server = actionlib.SimpleActionServer("navigate",NavigateAction, execute_cb=self.execute_cb, auto_start=False)
        self.hmm_nav_server.start()
    
  
    def execute_cb(self, goal):
        
        print (goal)
        x,y,th=goal.x ,goal.y,goal.yaw

        success = True
        result = NavigateActionResult()
        rate = rospy.Rate(1)
        timeout= rospy.Time.now().to_sec()+goal.timeout
        goal_pnt= PointStamped()
        goal_pnt.header.frame_id='map'
        goal_pnt.point.x , goal_pnt.point.y  =x,y
        pub_goal.publish(goal_pnt)

        
        
        while timeout >= rospy.Time.now().to_sec():     
            
            
            try:
                pose_robot,quat_robot=listener.lookupTransform('map', 'base_footprint', rospy.Time(0)) 
            except:
                print ('notf')
                pose_robot=np.zeros(3)
                quat_robot= np.zeros(4)
                quat_robot[-1]=1

            feed = pose2feedback(pose_robot,quat_robot)
            self.hmm_nav_server.publish_feedback(feed.feedback)
            
        print('is over')
        self.hmm_nav_server.set_succeeded(result.result)

            

        












        
if __name__=="__main__":
    global listener , pub ,pub2, pub3 , pub_goal
    rospy.init_node('hmm_navigation_actionlib_server')
    
    pub = rospy.Publisher('/hsrb/command_velocity', Twist, queue_size=1)
    pub2 = rospy.Publisher('/aa/Markov_NXT/', PointStamped, queue_size=1)  
    pub3= rospy.Publisher('aa/Markov_route',MarkerArray,queue_size=1)
    pub_goal= rospy.Publisher('/clicked_point',PointStamped,queue_size=1)
    listener = tf.TransformListener()
    
    
    s = HMM_navServer()
    rospy.spin()

    