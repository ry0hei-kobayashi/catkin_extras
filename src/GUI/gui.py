import PySimpleGUI as sg
import subprocess
import os
import signal

# bash command
def run_command(command):
    try:
        process = subprocess.Popen(["bash","-i" ,"-c", f'source ~/.bashrc && et && {command}'], preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process  # Return the process object
    except FileNotFoundError:
        sg.popup_error(f"Command '{command.split()[0]}' not found.", title="Error")
        return None

def kill_process(process):
    if process:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        return None

def cleanup(processes):
    for process in processes:
        kill_process(process)

layout = [
    [sg.Text("Press Button 1 to Run Navigation, Press Again to Kill Navigation")],
    [sg.Button("Button 1", key='-NAVIGATION-', button_color=('white', 'green'))],
    [sg.Text("Press Button 2 to Run Object Classification, Press Again to Kill Node")],
    [sg.Button("Button 2", key='-YOLO-', button_color=('white', 'green'))],
    [sg.Text("Press Button 3 to Run Moveit, Press Again to Kill Node")],
    [sg.Button("Button 3", key='-MOVEIT-', button_color=('white', 'green'))],
    [sg.Text("Press Button 4 to Run Moveit test arm, Press Again to Kill Node")],
    [sg.Button("Button 4", key='-MOVEIT_ARM-', button_color=('white', 'green'))],
    [sg.Image(key='-IMAGE-')],
]

window = sg.Window("ROS GUI", layout)

navigation_process = None
yolo_process = None
moveit_process = None
moveit_arm_process = None
processes = []

while True:
    event, _ = window.read()
    if event == sg.WINDOW_CLOSED:
        cleanup(processes)
        break
    elif event == '-NAVIGATION-':
        if navigation_process:
            navigation_process = kill_process(navigation_process)
            window['-NAVIGATION-'].update(button_color=('white', 'green'))
        else:
            navigation_process = run_command('roslaunch nav_pumas navigation_real.launch')
            window['-NAVIGATION-'].update(button_color=('white', 'red'))
            processes.append(navigation_process)
    elif event == '-YOLO-':
        if yolo_process:
            yolo_process = kill_process(yolo_process)
            window['-YOLO-'].update(button_color=('white', 'green'))
        else:
            yolo_process = run_command('rosrun object_classification classification_server.py')
            window['-YOLO-'].update(button_color=('white', 'red'))
            processes.append(yolo_process)
    elif event == '-MOVEIT-':
        if moveit_process:
            moveit_process = kill_process(moveit_process)
            window['-MOVEIT-'].update(button_color=('white', 'green'))
        else:
            moveit_process = run_command('roslaunch hsrb_moveit_config hsrb_demo_with_controller.launch')
            window['-MOVEIT-'].update(button_color=('white', 'red'))
            processes.append(moveit_process)

    elif event == '-MOVEIT_ARM-':
        if moveit_arm_process:
            moveit_arm_process = kill_process(moveit_arm_process)
            window['-MOVEIT_ARM-'].update(button_color=('white', 'green'))
        else:
            moveit_arm_process = run_command('roslaunch task arm_test.launch')
            window['-MOVEIT_ARM-'].update(button_color=('white', 'red'))
            processes.append(moveit_arm_process)

window.close()