# zoplete
Single-file flask app to deploy and manage kubernetes clusters (with flux and a marketplace)

☸️ Vanilla K8s Manager (Flask Edition)

Vanilla K8s Manager is a robust, single-file GUI tool designed to bootstrap, manage, and monitor "Vanilla" Kubernetes clusters on bare-metal servers or VMs.

Now powered by Flask and Material Design 3, it offers a modern, responsive interface to handle the complex process of setting up kubeadm clusters, managing worker nodes, and deploying complex data stacks via GitOps (FluxCD).

✨ Key Features

1. 🎨 Modern UI & UX
<img width="936" height="625" alt="image" src="https://github.com/user-attachments/assets/730eff05-eb57-45a8-8c55-4e57a7646ad7" />

Material Design 3: A clean, Google-inspired interface with responsive layouts, card-based dashboards, and smooth transitions.

Single-Page Application: Built as a lightweight SPA embedded within the Python backend.

2. 🛠️ Cluster Lifecycle

Master Bootstrap: One-click initialization of the Control Plane (Kubeadm, Containerd, Flannel CNI).

Smart OS Support: Automatically detects Debian/Ubuntu, RHEL/CentOS/Rocky, and SUSE to use the correct package managers.

Worker Onboarding: Generates custom Bash and Cloud-Init scripts to join new nodes effortlessly.

Node Management: View live node status (CPU/RAM in GiB) and detach worker nodes directly from the UI.

3. 🛍️ App Marketplace (GitOps)
<img width="936" height="1111" alt="image" src="https://github.com/user-attachments/assets/55bdb7f9-93fb-4ab5-9589-6040e63a4a24" />

FluxCD Integration: Automatically installs and manages Flux controllers.

One-Click Stack Deployment: Instantly deploy production-ready tools:

Apache Kafka (+ Kouncil UI)

Apache NiFi

Trino (Distributed SQL)

JupyterHub

Apache Airflow

Dependency Checks: Prevents installing apps (like Kouncil) if their dependencies (Kafka) are missing.

Access Management: Automatically discovers NodePorts and generates clickable links to access your deployed applications.

4. 📊 Observability

<img width="928" height="685" alt="image" src="https://github.com/user-attachments/assets/fb3ef153-2b29-42cf-99a2-9923cc787cde" />

Live Monitoring: Real-time, streaming charts for Cluster CPU and Memory usage.

Network Stats: Monitors network I/O on the Master node.

Metrics Server: One-click installation/patching of the Kubernetes Metrics Server.

💻 Prerequisites

Master Node (Host):

OS: Linux (Debian 11+, Ubuntu 20.04+, RHEL 8+, openSUSE).

Python: 3.8 or higher.

Privileges: Root/Sudo access is required for installation commands.

Hardware: Min 2 vCPUs, 2GB RAM.

Worker Nodes:

Hardware: Min 1 vCPU, 1GB RAM.

📥 Installation & Run

It is highly recommended to use a Python virtual environment to avoid conflicts with system packages.

1. Prepare Environment

# Install Python venv and Git
# (Debian/Ubuntu)
sudo apt update && sudo apt install -y python3-venv git

# (RHEL/CentOS)
sudo dnf install -y python3 git


2. Setup Directory

mkdir zoplete
cd zoplete
python3 -m venv venv
source venv/bin/activate


3. Install Dependencies

pip install flask kubernetes psutil pyyaml


4. Run the Manager

The application performs system-level operations (installing packages, modifying sysctl), so it must be run with sudo. Point sudo to your virtual environment's Python executable.

# Assuming you are in the k8s-manager directory
sudo ./venv/bin/python3 zoplete.py


5. Access

Open your web browser and navigate to:
http://<YOUR_VM_IP>:5000

🛡️ Security & disclaimer

This tool is intended for Day 0 / Day 1 operations (bootstrapping) in secure, private environments.

It runs with Root Privileges.

It exposes an unauthenticated web interface on port 5000.

Do not expose this to the public internet. Use a VPN or SSH Tunnel if accessing remotely.

🤝 Contributing

Feel free to fork and submit Pull Requests! This is a single-file application (k8s_manager.py) designed for simplicity and portability.
