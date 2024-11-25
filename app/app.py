import os
import subprocess
import sys
from flask import Flask, send_file, jsonify, request

app = Flask(__name__)

vm_list = {}


def get_vmlist():
    vm_list.clear()
    for filename in os.listdir('etc'):
        if filename.endswith('.conf'):
            vm_name = None
            config_data = {}
            with open(f'etc/{filename}', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    elif line.startswith('vm='):
                        vm_name = line.split('=')[1].strip()
                        continue
                    elif line.startswith('#') or line.startswith('extra'):
                        continue
                    elif '=' in line:
                        key, value = line.split('=', 1)
                        config_data[key.strip()] = value.strip()
            
            if vm_name is None:
                sys.exit(f"no vm field in {filename}")
            
            # Check if QEMU process is running 
            pid_file = f'qemu-{filename.replace(".conf", "")}.pid'
            status = 'running' if os.path.exists(pid_file) else 'stopped'

            vm_list[vm_name] = config_data
            vm_list[vm_name]['status'] = status

    return vm_list


def list_files(path):
    try:
        items = os.listdir(path)
        return jsonify(items)
    except FileNotFoundError:
        return jsonify({"error": "Directory not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

## routes

@app.route("/")
def index():
    # do not render template, frontend logic handled by Vue
    return send_file("index.html")


@app.route("/vmlist")
def vmlist():
    return jsonify(get_vmlist())


@app.route("/getkernels")
def getkernels():
    return list_files("kernels")


@app.route("/getimages")
def getimages():
    return list_files("images")


@app.route("/start", methods=["POST"])
def start_vm():
    vm_name = request.json.get("vm_name")

    config_file = f'etc/{vm_name}.conf'

    if not os.path.exists(config_file):
        return jsonify(
            {"success": False, "message": "Config file not found"}
        ), 404

    try:
        subprocess.Popen(["./startnb.sh", "-f", config_file, "-d"])
        return jsonify({"success": True, "message": "Starting VM"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/stop", methods=["POST"])
def stop_vm():
    vm_name = request.json.get("vm_name")

    pid_file = f'qemu-{vm_name}.pid'

    if not os.path.exists(pid_file):
        return jsonify(
            {"success": False, "message": "PID file not found"}
        ), 404

    try:
        with open(pid_file, 'r') as f:
            pid = f.read().strip()
        os.kill(int(pid), 15)
        return jsonify({"success": True, "message": "Stopping VM"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/saveconf", methods=['POST'])
def saveconf():
    try:
        data = request.get_json()
        if not data:
            return jsonify(
                {"success": False, "message": "No JSON payload provided"}
            ), 400

        vm_name = data.get("vm")
        if not vm_name:
            return jsonify(
                {
                    "success": False,
                    "message": "'vm' key is required in the JSON payload"
                }
            ), 400

        directory = './etc'
        os.makedirs(directory, exist_ok=True)
        file_path = os.path.join(directory, f"{vm_name}.conf")

        with open(file_path, 'w') as file:
            for key, value in data.items():
                file.write(f"{key}={value}\n")
            file.write('extra="-pidfile qemu-${vm}.pid" \n')

        return jsonify({"success": True, "message": file_path}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/rm/<vm>', methods=['DELETE'])
def rm_file(vm):
    try:
        filepath = f"etc/{vm}.conf"

        if not os.path.isfile(filepath):
            return jsonify(
                {"success": False, "message": f"'{vm}' not found"}
            ), 404

        os.remove(filepath)
        return jsonify(
            {"success": True, "message": f"'{vm}' deleted successfully"}
        ), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":

    os.chdir("..");
    vm_list = get_vmlist()
 
    app.run(host='0.0.0.0')
