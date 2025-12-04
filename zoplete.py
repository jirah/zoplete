import os
import re
import time
import yaml
import socket
import psutil
import datetime
import subprocess
import threading
import json
from flask import Flask, Response, request, jsonify, stream_with_context
from kubernetes import client, config

# --- CONFIGURATION ---
app = Flask(__name__)

# --- FRONTEND TEMPLATE (Material Design 3) ---
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zoplete - K8s Manager</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --md-sys-color-primary: #00639a;
            --md-sys-color-on-primary: #ffffff;
            --md-sys-color-primary-container: #cee5ff;
            --md-sys-color-on-primary-container: #001d32;
            --md-sys-color-secondary: #51606f;
            --md-sys-color-secondary-container: #d5e4f7;
            --md-sys-color-on-secondary-container: #0e1d2a;
            --md-sys-color-surface: #fcfcff;
            --md-sys-color-on-surface: #1a1c1e;
            --md-sys-color-surface-variant: #dee3eb;
            --md-sys-color-outline: #72777f;
            --radius-lg: 16px;
        }
        body { font-family: 'Roboto', sans-serif; background-color: var(--md-sys-color-surface); margin: 0; display: flex; height: 100vh; color: var(--md-sys-color-on-surface); }
        
        /* Nav */
        .nav-rail { width: 80px; border-right: 1px solid var(--md-sys-color-surface-variant); display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
        .nav-item { width: 56px; height: 56px; display: flex; flex-direction: column; align-items: center; justify-content: center; border-radius: 16px; margin-bottom: 12px; cursor: pointer; color: #444; }
        .nav-item.active { background-color: var(--md-sys-color-primary-container); color: var(--md-sys-color-on-primary-container); }
        .nav-label { font-size: 11px; margin-top: 4px; font-weight: 500; }
        
        /* Main */
        .main-content { flex: 1; padding: 24px; overflow-y: auto; }
        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.3s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        /* Components */
        .btn { height: 40px; padding: 0 24px; border-radius: 20px; border: none; cursor: pointer; font-weight: 500; display: inline-flex; align-items: center; gap: 8px; font-family: 'Roboto'; transition: 0.2s; }
        .btn-filled { background: var(--md-sys-color-primary); color: white; }
        .btn-filled:hover { box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        .btn-tonal { background: var(--md-sys-color-secondary-container); color: var(--md-sys-color-on-secondary-container); }
        .btn-text { background: none; color: var(--md-sys-color-primary); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .card { background: #f0f4fa; border-radius: 16px; padding: 24px; margin-bottom: 24px; }
        .info-box { background: var(--md-sys-color-secondary-container); color: var(--md-sys-color-on-secondary-container); padding: 16px; border-radius: 12px; display: flex; align-items: center; gap: 12px; margin-bottom: 24px; }
        
        select { padding: 8px 12px; border-radius: 8px; border: 1px solid #ccc; font-family: 'Roboto'; font-size: 14px; background: white; margin-left: 12px; }

        /* Tables */
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { text-align: left; padding: 12px; background: var(--md-sys-color-surface-variant); border-radius: 4px; }
        td { padding: 12px; border-bottom: 1px solid #eee; }
        .chip { padding: 4px 12px; border-radius: 8px; font-size: 12px; font-weight: 500; }
        .chip-success { background: #e6f4ea; color: #137333; }
        .chip-warning { background: #fef7e0; color: #ea8600; }
        .chip-error { background: #fce8e6; color: #c5221f; }

        /* Terminal */
        #terminal { background: #1e1e1e; color: #0f0; padding: 16px; border-radius: 8px; font-family: monospace; height: 300px; overflow-y: auto; display: none; margin-top: 16px; white-space: pre-wrap; }
        
        /* Grid */
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 24px; }

        /* Pulsing Dot */
        .live-dot { width: 10px; height: 10px; background: #4caf50; border-radius: 50%; display: inline-block; animation: pulse 1.5s infinite; margin-left: 8px; }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(76, 175, 80, 0); } 100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0); } }

        /* Spin */
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <nav class="nav-rail">
        <img src="https://raw.githubusercontent.com/cncf/artwork/master/projects/kubernetes/icon/color/kubernetes-icon-color.png" width="40" style="margin-bottom: 40px;">
        <div class="nav-item active" onclick="switchTab('dashboard', this)">
            <span class="material-symbols-outlined">grid_view</span><span class="nav-label">Cluster</span>
        </div>
        <div class="nav-item" onclick="switchTab('marketplace', this)">
            <span class="material-symbols-outlined">storefront</span><span class="nav-label">Apps</span>
        </div>
        <div class="nav-item" onclick="switchTab('monitor', this)">
            <span class="material-symbols-outlined">monitoring</span><span class="nav-label">Monitor</span>
        </div>
        <div class="nav-item" onclick="switchTab('settings', this)">
            <span class="material-symbols-outlined">settings</span><span class="nav-label">Settings</span>
        </div>
        <div class="nav-item" onclick="switchTab('info', this)">
            <span class="material-symbols-outlined">info</span><span class="nav-label">Info</span>
        </div>
    </nav>

    <main class="main-content">
        <header style="margin-bottom: 30px;">
            <h1 style="margin:0;">Zoplete</h1>
            <div id="os-info" style="font-size: 14px; color: #666; margin-top: 4px;">K8s Manager</div>
        </header>

        <!-- DASHBOARD TAB -->
        <div id="dashboard" class="page active">
            <div id="cluster-status-box" class="info-box" style="display:none;">
                <span class="material-symbols-outlined">check_circle</span>
                <div><strong>Cluster is Active</strong><br>Kubernetes Master is running.</div>
            </div>
            
            <div id="install-box">
                <div class="card">
                    <h2>⚠️ Cluster Not Detected</h2>
                    <p>Kubernetes is not initialized on this machine.</p>
                    <button class="btn btn-filled" onclick="installMaster()">
                        <span class="material-symbols-outlined">build</span> Initialize Master Node
                    </button>
                    <div id="terminal"></div>
                </div>
            </div>

            <div id="node-view" style="display:none;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                    <h2>Cluster Nodes</h2>
                    <button class="btn btn-tonal" onclick="loadNodes()"><span class="material-symbols-outlined">refresh</span> Refresh</button>
                </div>
                <div style="border: 1px solid #ddd; border-radius: 12px; overflow: hidden;">
                    <table id="node-table">
                        <thead>
                            <tr><th>Name</th><th>Role</th><th>Status</th><th>IP</th><th>CPU</th><th>RAM</th><th>Action</th></tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>

                <div class="card" style="margin-top: 24px;">
                    <h3>Add Worker Nodes</h3>
                    <p>Run the generated script on new VMs to join them to this cluster.</p>
                    <div style="display:flex; gap: 12px;">
                        <select id="worker-os" class="btn" style="border:1px solid #ccc;">
                            <option value="debian">Debian/Ubuntu</option>
                            <option value="rhel">RHEL/CentOS</option>
                            <option value="suse">SUSE</option>
                        </select>
                        <button class="btn btn-tonal" onclick="downloadScript('sh')">Download Bash Script</button>
                        <button class="btn btn-tonal" onclick="downloadScript('yaml')">Download Cloud-Init</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- MARKETPLACE TAB -->
        <div id="marketplace" class="page">
            <div style="display:flex; justify-content:space-between; margin-bottom:16px;">
                <h2>App Marketplace</h2>
                <span id="flux-status" class="chip chip-warning">Checking Flux...</span>
            </div>
            <div id="flux-install-prompt" class="card" style="display:none; text-align:center;">
                <h3>FluxCD Required</h3>
                <p>You must install FluxCD (via Settings) to use the Marketplace.</p>
                <button class="btn btn-filled" onclick="switchTab('settings', document.querySelector('.nav-item:nth-child(4)'))">Go to Settings</button>
            </div>
            <div id="app-grid" class="grid">
                <!-- App cards injected via JS -->
            </div>
        </div>

        <!-- MONITOR TAB -->
        <div id="monitor" class="page">
            <div style="display:flex; align-items:center; margin-bottom:16px;">
                <h2 style="margin:0;">Cluster Observability</h2>
                <div id="live-indicator" class="live-dot" style="display:none;"></div>
                
                <!-- View Selector -->
                <div style="margin-left: auto; display: flex; align-items: center;">
                    <label for="monitor-view-select" style="font-size:14px; font-weight:500;">View Mode:</label>
                    <select id="monitor-view-select" onchange="resetCharts()">
                        <option value="total">Cluster Total (Aggregated)</option>
                        <option value="all">All Nodes (Detailed)</option>
                        <!-- Nodes injected via JS -->
                    </select>
                </div>
            </div>
            
             <div id="metrics-install-prompt" class="card" style="display:none; text-align:center;">
                <h3>Metrics Server Required</h3>
                <p>Real-time charts require the Kubernetes Metrics Server.</p>
                <button id="btn-install-metrics" class="btn btn-filled" onclick="installMetrics()">
                    Install Metrics Server
                </button>
            </div>
            
            <div id="charts-view">
                <div class="card">
                    <canvas id="cpuChart" height="100"></canvas>
                </div>
                <div class="card">
                    <canvas id="memChart" height="100"></canvas>
                </div>
                <div class="card">
                    <canvas id="netChart" height="100"></canvas>
                </div>
            </div>
        </div>

        <!-- SETTINGS TAB (GitOps) -->
        <div id="settings" class="page">
            <h2>Settings & GitOps</h2>
            
            <!-- Flux Status -->
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h3>GitOps Engine (FluxCD)</h3>
                        <p style="color:#666;">Manage cluster state via Git repositories.</p>
                    </div>
                    <div id="settings-flux-status">
                         <!-- Injected via JS -->
                    </div>
                </div>
            </div>

            <div id="gitops-dashboard" style="display:none;">
                <!-- Source Management -->
                <h3>🔗 Git Sources (Repositories)</h3>
                <div id="git-sources-table" style="border: 1px solid #ddd; border-radius: 12px; overflow: hidden; margin-bottom: 24px;">
                    <!-- Table injected via JS -->
                </div>
                
                <div class="card">
                    <h3>➕ Connect New Repository</h3>
                    <form onsubmit="connectRepo(event)" style="display:flex; gap:12px; align-items:end;">
                        <div>
                            <label style="font-size:12px; font-weight:500;">Name</label><br>
                            <input type="text" id="src_name" placeholder="e.g. podinfo" required style="padding:8px; border-radius:8px; border:1px solid #ccc;">
                        </div>
                        <div style="flex:1;">
                            <label style="font-size:12px; font-weight:500;">Git URL</label><br>
                            <input type="text" id="src_url" placeholder="https://github.com/user/repo" required style="width:100%; padding:8px; border-radius:8px; border:1px solid #ccc;">
                        </div>
                        <div>
                            <label style="font-size:12px; font-weight:500;">Branch</label><br>
                            <input type="text" id="src_branch" value="main" required style="padding:8px; border-radius:8px; border:1px solid #ccc; width:80px;">
                        </div>
                        <button type="submit" class="btn btn-filled">Connect</button>
                    </form>
                </div>

                <hr style="margin: 32px 0; border:0; border-top:1px solid #eee;">

                <!-- App Management -->
                <h3>📦 Applications (Kustomizations)</h3>
                <div id="kustomizations-list">
                    <!-- Cards injected via JS -->
                </div>

                <div class="card" style="margin-top:24px;">
                    <h3>➕ Deploy Application from Git</h3>
                    <form onsubmit="createKust(event)" style="display:flex; gap:12px; align-items:end;">
                        <div>
                            <label style="font-size:12px; font-weight:500;">App Name</label><br>
                            <input type="text" id="k_name" required style="padding:8px; border-radius:8px; border:1px solid #ccc;">
                        </div>
                        <div>
                            <label style="font-size:12px; font-weight:500;">Source</label><br>
                            <select id="k_source" style="padding:8px; border-radius:8px; border:1px solid #ccc; margin:0; width:150px;"></select>
                        </div>
                        <div style="flex:1;">
                            <label style="font-size:12px; font-weight:500;">Path in Repo</label><br>
                            <input type="text" id="k_path" value="./" required style="width:100%; padding:8px; border-radius:8px; border:1px solid #ccc;">
                        </div>
                        <button type="submit" class="btn btn-filled">Deploy</button>
                    </form>
                </div>
            </div>
        </div>

        <!-- INFO TAB -->
        <div id="info" class="page">
            <h2>Requirements</h2>
            <div class="grid">
                <div class="card">
                    <h3>Master Node</h3>
                    <ul><li>2 CPUs</li><li>2 GB RAM</li><li>Swap Disabled</li></ul>
                </div>
                <div class="card">
                    <h3>Worker Node</h3>
                    <ul><li>1 CPU</li><li>1 GB RAM</li><li>Swap Disabled</li></ul>
                </div>
            </div>
        </div>
    </main>

    <script>
        // --- GLOBAL STATE ---
        let isMonitoring = false;
        let charts = {};
        let knownNodes = [];
        let lastNetwork = { sent: 0, recv: 0, time: 0 };
        let fluxInstalled = false;

        // --- NAVIGATION ---
        function switchTab(tabId, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            if(el) el.classList.add('active');
            
            // Auto-start monitor if on monitor tab
            if (tabId === 'monitor') startMonitoring();
            else stopMonitoring();
            
            // Loaders
            if (tabId === 'marketplace') loadMarketplace();
            if (tabId === 'settings') loadSettings();
        }

        // --- INITIAL LOAD ---
        async function init() {
            const res = await fetch('/api/init');
            const data = await res.json();
            document.getElementById('os-info').innerText = data.os_info.PRETTY_NAME + " (Running)";
            
            if (data.is_ready) {
                document.getElementById('cluster-status-box').style.display = 'flex';
                document.getElementById('install-box').style.display = 'none';
                document.getElementById('node-view').style.display = 'block';
                loadNodes();
            }
            
            // Check Flux status globally
            const mktRes = await fetch('/api/marketplace');
            const mktData = await mktRes.json();
            fluxInstalled = mktData.flux_installed;
        }

        // --- DASHBOARD ---
        async function loadNodes() {
            const res = await fetch('/api/nodes');
            const nodes = await res.json();
            const tbody = document.querySelector('#node-table tbody');
            tbody.innerHTML = '';
            
            knownNodes = nodes.map(n => n.Name);
            updateMonitorDropdown(); // Populate monitor dropdown

            if (nodes.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center">No nodes found.</td></tr>';
                return;
            }

            nodes.forEach(n => {
                const statusClass = n.Status === 'Ready' ? 'chip-success' : 'chip-warning';
                const delBtn = n.Role === 'Master' 
                    ? `<button class="btn-text" disabled>Locked</button>`
                    : `<button class="btn-text" style="color:#ba1a1a" onclick="deleteNode('${n.Name}')">Detach</button>`;
                
                const tr = `<tr>
                    <td><strong>${n.Name}</strong></td>
                    <td>${n.Role}</td>
                    <td><span class="chip ${statusClass}">${n.Status}</span></td>
                    <td>${n['Internal IP']}</td>
                    <td>${n.CPU}</td>
                    <td>${n.Memory}</td>
                    <td>${delBtn}</td>
                </tr>`;
                tbody.innerHTML += tr;
            });
        }
        
        function updateMonitorDropdown() {
            const select = document.getElementById('monitor-view-select');
            // Keep first 2 options (Total, All)
            while (select.options.length > 2) { select.remove(2); }
            
            knownNodes.forEach(name => {
                const opt = document.createElement('option');
                opt.value = name;
                opt.innerText = `Node: ${name}`;
                select.appendChild(opt);
            });
        }

        async function installMaster() {
            const term = document.getElementById('terminal');
            term.style.display = 'block';
            term.innerText = 'Starting Installation...\n';
            
            const response = await fetch('/api/install-master', { method: 'POST' });
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                const text = decoder.decode(value);
                term.innerText += text;
                term.scrollTop = term.scrollHeight;
            }
            
            init(); // Reload state
        }

        async function deleteNode(name) {
            if(!confirm('Detach ' + name + '?')) return;
            await fetch('/api/nodes/' + name, { method: 'DELETE' });
            loadNodes();
        }
        
        function downloadScript(type) {
            const os = document.getElementById('worker-os').value;
            window.location.href = `/api/download-worker?type=${type}&os=${os}`;
        }

        // --- SETTINGS (GitOps) ---
        async function loadSettings() {
            // Refresh flux status
            const res = await fetch('/api/marketplace'); // reusing endpoint for status
            const data = await res.json();
            fluxInstalled = data.flux_installed;

            const statusDiv = document.getElementById('settings-flux-status');
            const dashDiv = document.getElementById('gitops-dashboard');

            if (fluxInstalled) {
                statusDiv.innerHTML = '<span class="chip chip-success">Active</span>';
                dashDiv.style.display = 'block';
                loadGitSources();
                loadKustomizations();
            } else {
                statusDiv.innerHTML = '<button class="btn btn-filled" onclick="installFluxSettings()">Install FluxCD</button>';
                dashDiv.style.display = 'none';
            }
        }

        async function installFluxSettings() {
            const statusDiv = document.getElementById('settings-flux-status');
            statusDiv.innerHTML = '<span class="chip chip-warning">Installing...</span>';
            await fetch('/api/install-flux', { method: 'POST' });
            setTimeout(loadSettings, 2000);
        }

        async function loadGitSources() {
            const res = await fetch('/api/git-sources');
            const sources = await res.json();
            
            // Update UI Table
            let html = '<table style="width:100%"><thead><tr><th>Name</th><th>URL</th><th>Status</th></tr></thead><tbody>';
            const select = document.getElementById('k_source');
            select.innerHTML = '';

            if (sources.length === 0) html += '<tr><td colspan="3">No repositories connected.</td></tr>';
            
            sources.forEach(s => {
                html += `<tr><td>${s.Name}</td><td>${s.URL}</td><td>${s.Status}</td></tr>`;
                // Populate dropdown for app deployment
                const opt = document.createElement('option');
                opt.value = s.Name;
                opt.innerText = s.Name;
                select.appendChild(opt);
            });
            html += '</tbody></table>';
            document.getElementById('git-sources-table').innerHTML = html;
        }

        async function loadKustomizations() {
            const res = await fetch('/api/kustomizations');
            const kusts = await res.json();
            const list = document.getElementById('kustomizations-list');
            list.innerHTML = '';

            if (kusts.length === 0) {
                list.innerHTML = '<div style="padding:12px; color:#666;">No applications deployed.</div>';
                return;
            }

            kusts.forEach(k => {
                const statusColor = k.Status === 'Ready' ? '#4caf50' : '#f44336';
                const item = `
                <div class="card" style="display:flex; justify-content:space-between; align-items:center; padding:16px; margin-bottom:12px;">
                    <div style="display:flex; align-items:center; gap:12px;">
                         <div style="width:12px; height:12px; border-radius:50%; background:${statusColor}"></div>
                         <div>
                            <div style="font-weight:500">${k.Name}</div>
                            <div style="font-size:12px; color:#666;">${k.Source} / ${k.Path}</div>
                         </div>
                    </div>
                    <div>
                        <div style="font-size:12px; text-align:right;">${k.Revision.substring(0,7)}</div>
                        <button class="btn-text" onclick="syncKust('${k.Name}')">Sync Now</button>
                    </div>
                </div>`;
                list.innerHTML += item;
            });
        }

        async function connectRepo(e) {
            e.preventDefault();
            const name = document.getElementById('src_name').value;
            const url = document.getElementById('src_url').value;
            const branch = document.getElementById('src_branch').value;
            
            await fetch('/api/create-source', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name, url, branch })
            });
            loadSettings();
        }

        async function createKust(e) {
            e.preventDefault();
            const name = document.getElementById('k_name').value;
            const source = document.getElementById('k_source').value;
            const path = document.getElementById('k_path').value;

            await fetch('/api/create-kust', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name, source, path })
            });
            loadSettings();
        }

        async function syncKust(name) {
             await fetch('/api/sync-kust', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name })
            });
            alert('Sync Triggered');
            setTimeout(loadSettings, 2000);
        }

        // --- MARKETPLACE ---
        async function loadMarketplace() {
            const res = await fetch('/api/marketplace');
            const data = await res.json();
            
            const fluxStatus = document.getElementById('flux-status');
            const appGrid = document.getElementById('app-grid');
            const installPrompt = document.getElementById('flux-install-prompt');

            if (!data.flux_installed) {
                fluxStatus.className = 'chip chip-error';
                fluxStatus.innerText = 'Flux Missing';
                installPrompt.style.display = 'block';
                appGrid.style.display = 'none';
                return;
            }

            fluxStatus.className = 'chip chip-success';
            fluxStatus.innerText = 'Flux Active';
            installPrompt.style.display = 'none';
            appGrid.style.display = 'grid';
            appGrid.innerHTML = '';

            // Render Apps
            for (const [key, app] of Object.entries(data.catalog)) {
                const isInstalled = data.installed_apps.includes(key);
                let accessInfo = '';
                let disabled = false;
                let btnLabel = 'Install';
                let btnClass = 'btn-filled';

                // Dependency Check
                if (app.dependency && !data.installed_apps.includes(app.dependency)) {
                    disabled = true;
                    btnLabel = `Requires ${app.dependency}`;
                    btnClass = 'btn-tonal';
                }

                if (isInstalled) {
                    btnLabel = 'Uninstall';
                    btnClass = 'btn-text';
                    
                    // Access info
                    if (app.ui_svc) {
                        const port = data.services[key];
                        if (port) {
                            // Build Link (Hostname agnostic)
                             const url = `http://${window.location.hostname}:${port}`;
                             accessInfo = `<div style="margin-top:12px; padding:8px; background:#fff; border-radius:8px; font-size:12px;">
                                <strong>Access:</strong> <a href="${url}" target="_blank">${url}</a>
                             </div>`;
                        } else {
                             accessInfo = `<div style="margin-top:12px; font-size:12px; color:orange;">Waiting for Port...</div>`;
                        }
                    }
                }
                
                let logoHtml = '';
                if (app.logo_url) {
                    logoHtml = `<img src="${app.logo_url}" style="width:48px; height:48px; object-fit:contain; margin-right:12px;">`;
                } else {
                     logoHtml = `<div style="width:40px; height:40px; background:#e1f5fe; border-radius:50%; display:flex; align-items:center; justify-content:center; margin-right:12px; font-weight:bold; color:#0277bd;">${key[0].toUpperCase()}</div>`;
                }

                const card = `
                <div class="card" style="height:auto;">
                    <div class="card-header">
                        ${logoHtml}
                        <div>
                            <div style="font-weight:500; font-size:16px;">${app.title}</div>
                            <div style="font-size:12px; color:#666;">${app.version}</div>
                        </div>
                    </div>
                    <p style="font-size:14px; color:#444; height:40px; overflow:hidden;">${app.desc}</p>
                    ${accessInfo}
                    <div style="margin-top:16px; display:flex; justify-content:flex-end;">
                        <button class="btn ${btnClass}" ${disabled ? 'disabled' : ''} 
                            onclick="toggleApp('${key}', ${isInstalled})">
                            ${btnLabel}
                        </button>
                    </div>
                </div>`;
                appGrid.innerHTML += card;
            }
        }

        async function installFlux() {
            await fetch('/api/install-flux', { method: 'POST' });
            setTimeout(loadMarketplace, 2000);
        }

        async function toggleApp(key, isInstalled) {
            const endpoint = isInstalled ? '/api/uninstall-app' : '/api/install-app';
            try {
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ app_key: key })
                });
                const data = await res.json();
                if (data.status !== 'ok') {
                    alert('Operation Failed: ' + (data.error || 'Unknown error'));
                }
            } catch(e) {
                alert('Request Failed: ' + e);
            }
            setTimeout(loadMarketplace, 2000);
        }

        // --- MONITOR ---
        function startMonitoring() {
            if (isMonitoring) return;
            isMonitoring = true;
            document.getElementById('live-indicator').style.display = 'inline-block';
            
            // Initialize charts if not already done
            if (!charts.cpu) {
                const ctxCpu = document.getElementById('cpuChart').getContext('2d');
                const ctxMem = document.getElementById('memChart').getContext('2d');
                const ctxNet = document.getElementById('netChart').getContext('2d');
                
                const commonOpt = { responsive: true, maintainAspectRatio: false, animation: false };
                
                charts.cpu = new Chart(ctxCpu, { type: 'line', data: { labels: [], datasets: [] }, options: { ...commonOpt, plugins: { title: { display: true, text: 'CPU Usage (Cores)' } }, scales: { y: { suggestedMin: 0 } } } });
                charts.mem = new Chart(ctxMem, { type: 'line', data: { labels: [], datasets: [] }, options: { ...commonOpt, plugins: { title: { display: true, text: 'Memory Usage (MiB)' } }, scales: { y: { suggestedMin: 0 } } } });
                charts.net = new Chart(ctxNet, { type: 'line', data: { labels: [], datasets: [] }, options: { ...commonOpt, plugins: { title: { display: true, text: 'Network I/O (MB/s - Master)' } }, scales: { y: { beginAtZero: true } } } });
            }

            pollMetrics();
        }

        function stopMonitoring() { 
            isMonitoring = false; 
            document.getElementById('live-indicator').style.display = 'none';
        }
        
        function resetCharts() {
            if (charts.cpu) {
                charts.cpu.data.datasets = [];
                charts.mem.data.datasets = [];
            }
        }

        async function pollMetrics() {
            if (!isMonitoring) return;
            
            try {
                const res = await fetch('/api/metrics');
                const data = await res.json();
                
                if (!data.has_metrics) {
                    document.getElementById('metrics-install-prompt').style.display = 'block';
                    document.getElementById('charts-view').style.display = 'none';
                } else {
                    document.getElementById('metrics-install-prompt').style.display = 'none';
                    document.getElementById('charts-view').style.display = 'block';
                    updateCharts(data.metrics, data.network);
                }
            } catch(e) { console.log(e); }
            
            if (isMonitoring) setTimeout(pollMetrics, 2000);
        }

        function updateCharts(metrics, network) {
            const timeLabel = new Date().toLocaleTimeString();
            const viewMode = document.getElementById('monitor-view-select').value;
            
            if (charts.cpu.data.labels.length > 20) {
                charts.cpu.data.labels.shift();
                charts.mem.data.labels.shift();
                charts.net.data.labels.shift();
            }
            
            charts.cpu.data.labels.push(timeLabel);
            charts.mem.data.labels.push(timeLabel);
            charts.net.data.labels.push(timeLabel);

            // Net Chart
            let netSent = charts.net.data.datasets.find(d => d.label === 'Sent (MB/s)');
            let netRecv = charts.net.data.datasets.find(d => d.label === 'Recv (MB/s)');
            
            if (!netSent) {
                netSent = { label: 'Sent (MB/s)', data: [], borderColor: '#4caf50', fill: false };
                netRecv = { label: 'Recv (MB/s)', data: [], borderColor: '#2196f3', fill: false };
                charts.net.data.datasets.push(netSent, netRecv);
            }
            
            if (netSent.data.length > 20) { netSent.data.shift(); netRecv.data.shift(); }

            // Calculate Rate
            const now = Date.now();
            let sentRate = 0;
            let recvRate = 0;
            
            if (lastNetwork.time !== 0) {
                const seconds = (now - lastNetwork.time) / 1000;
                if (seconds > 0) {
                    sentRate = (network.sent - lastNetwork.sent) / seconds;
                    recvRate = (network.recv - lastNetwork.recv) / seconds;
                }
            }
            lastNetwork = { sent: network.sent, recv: network.recv, time: now };
            if (sentRate < 0) sentRate = 0;
            if (recvRate < 0) recvRate = 0;

            netSent.data.push(sentRate);
            netRecv.data.push(recvRate);
            charts.net.update();

            // Metrics
            if (viewMode === 'total') {
                let totalCpu = 0;
                let totalMem = 0;
                metrics.forEach(n => { totalCpu += n['CPU (cores)']; totalMem += n['Memory (MiB)']; });
                
                updateDataset(charts.cpu, 'Cluster Total', totalCpu, '#00639a', true);
                updateDataset(charts.mem, 'Cluster Total', totalMem, '#00639a', true);
                
                charts.cpu.data.datasets = charts.cpu.data.datasets.filter(d => d.label === 'Cluster Total');
                charts.mem.data.datasets = charts.mem.data.datasets.filter(d => d.label === 'Cluster Total');
                
            } else if (viewMode === 'all') {
                 metrics.forEach((node, index) => {
                    const colors = ['#00639a', '#ba1a1a', '#00695c', '#e65100', '#6a1b9a'];
                    const color = colors[index % colors.length];
                    updateDataset(charts.cpu, node.Name, node['CPU (cores)'], color, false);
                    updateDataset(charts.mem, node.Name, node['Memory (MiB)'], color, false);
                 });
                 charts.cpu.data.datasets = charts.cpu.data.datasets.filter(d => metrics.find(m => m.Name === d.label));
                 charts.mem.data.datasets = charts.mem.data.datasets.filter(d => metrics.find(m => m.Name === d.label));

            } else {
                const node = metrics.find(n => n.Name === viewMode);
                if (node) {
                    updateDataset(charts.cpu, node.Name, node['CPU (cores)'], '#00639a', true);
                    updateDataset(charts.mem, node.Name, node['Memory (MiB)'], '#00639a', true);
                    charts.cpu.data.datasets = charts.cpu.data.datasets.filter(d => d.label === node.Name);
                    charts.mem.data.datasets = charts.mem.data.datasets.filter(d => d.label === node.Name);
                }
            }

            charts.cpu.update();
            charts.mem.update();
        }
        
        function updateDataset(chart, label, value, color, fill) {
            let ds = chart.data.datasets.find(d => d.label === label);
            if (!ds) {
                ds = { label: label, data: [], borderColor: color, tension: 0.3, fill: fill, backgroundColor: fill ? color + '33' : undefined };
                chart.data.datasets.push(ds);
            }
            if (ds.data.length > 20) ds.data.shift();
            ds.data.push(value);
        }
        
        async function installMetrics() {
            const btn = document.getElementById('btn-install-metrics');
            btn.disabled = true;
            btn.innerHTML = '<span class="material-symbols-outlined spin">refresh</span> Installing...';
            try {
                await fetch('/api/install-metrics', { method: 'POST' });
            } catch (e) {
                alert("Install Failed: " + e);
                btn.disabled = false;
                btn.innerHTML = 'Install Metrics Server';
            }
        }

        window.onload = init;
    </script>
</body>
</html>
"""

# --- PYTHON LOGIC ---
def detect_os_release():
    os_info = {"ID": "unknown", "VERSION_ID": "unknown", "PRETTY_NAME": "Unknown Linux", "FAMILY": "unknown"}
    try:
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        v = v.strip('"').strip("'")
                        os_info[k] = v
        os_id = os_info.get("ID", "").lower()
        if os_id in ["ubuntu", "debian", "pop", "kali"]: os_info["FAMILY"] = "debian"
        elif os_id in ["rhel", "centos", "rocky", "fedora"]: os_info["FAMILY"] = "rhel"
        elif os_id in ["sles", "opensuse", "opensuse-leap"]: os_info["FAMILY"] = "suse"
    except: pass
    return os_info

def run_shell_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return res.returncode == 0, res.stdout
    except Exception as e: return False, str(e)

def stream_shell_cmd(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in process.stdout:
        yield line

def get_detailed_nodes():
    try:
        if os.path.exists("/etc/kubernetes/admin.conf"):
            config.load_kube_config(config_file="/etc/kubernetes/admin.conf")
        api = client.CoreV1Api()
        nodes = api.list_node()
        data = []
        for n in nodes.items:
            role = "Worker"
            if "node-role.kubernetes.io/control-plane" in n.metadata.labels: role = "Master"
            status = "NotReady"
            for c in n.status.conditions:
                if c.type == "Ready" and c.status == "True": status = "Ready"
            ip = next((a.address for a in n.status.addresses if a.type == "InternalIP"), "Unknown")
            mem_kb = int(n.status.capacity['memory'].replace('Ki',''))
            mem_gib = f"{mem_kb / (1024*1024):.2f} GiB"
            data.append({
                "Name": n.metadata.name,
                "Role": role,
                "Status": status,
                "Internal IP": ip,
                "CPU": n.status.capacity['cpu'],
                "Memory": mem_gib
            })
        return data
    except: return []

def get_public_ip_metadata():
    try:
        cmd_token = 'curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" -s --fail'
        token_res = subprocess.run(cmd_token, shell=True, stdout=subprocess.PIPE, text=True, timeout=1)
        if token_res.returncode != 0: return None
        token = token_res.stdout.strip()
        cmd_ip = f'curl -H "X-aws-ec2-metadata-token: {token}" http://169.254.169.254/latest/meta-data/public-ipv4 -s --fail'
        ip_res = subprocess.run(cmd_ip, shell=True, stdout=subprocess.PIPE, text=True, timeout=1)
        if ip_res.returncode == 0: return ip_res.stdout.strip()
    except: pass
    return None

def get_node_ips():
    ips = []
    try:
        if os.path.exists("/etc/kubernetes/admin.conf"):
            try: config.load_kube_config(config_file="/etc/kubernetes/admin.conf")
            except: pass
        api = client.CoreV1Api()
        nodes = api.list_node()
        for node in nodes.items:
            ext_ip = None
            int_ip = None
            for addr in node.status.addresses:
                if addr.type == "ExternalIP": ext_ip = addr.address
                if addr.type == "InternalIP": int_ip = addr.address
            if ext_ip: ips.append(ext_ip)
            elif int_ip: ips.append(int_ip)
    except Exception: pass
    public_ip = get_public_ip_metadata()
    if public_ip: ips.insert(0, public_ip)
    return list(set(ips))

def get_k8s_install_cmd(os_family):
    if os_family == "debian":
        return """
    sudo rm -f /etc/apt/sources.list.d/kubernetes.list
    sudo apt-get update && sudo apt-get install -y apt-transport-https ca-certificates curl gpg
    curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor --yes -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
    echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
    sudo apt-get update
    sudo apt-get install -y kubelet kubeadm kubectl
    sudo apt-mark hold kubelet kubeadm kubectl
    """
    # ... other families same as before
    return "# Manual Installation Required"

# --- CATALOG & GITOPS LOGIC ---
MARKETPLACE_CATALOG = {
    "kafka": { "title": "Apache Kafka", "desc": "Event streaming platform.", "chart": "kafka", "repo_url": "https://charts.bitnami.com/bitnami", "repo_name": "bitnami", "version": "26.0.0", "values": {"zookeeper": {"enabled": True}, "replicaCount": 1}, "ui_svc": None, "logo_url": "https://upload.wikimedia.org/wikipedia/commons/0/01/Apache_Kafka_logo.svg"},
    "kouncil": { "title": "Kouncil", "desc": "Kafka UI. Requires Kafka.", "chart": "kouncil", "repo_url": "https://consdata.github.io/kouncil/", "repo_name": "consdata", "version": "1.5.0", "values": {"bootstrapServers": "kafka.flux-system.svc.cluster.local:9092", "service": {"type": "NodePort"}}, "ui_svc": "kouncil", "dependency": "kafka", "logo_url": "https://avatars.githubusercontent.com/u/47789366?s=200&v=4"},
    "jupyterhub": { "title": "JupyterHub", "desc": "Notebook server.", "chart": "jupyterhub", "repo_url": "https://jupyterhub.github.io/helm-chart/", "repo_name": "jupyterhub", "version": "3.1.0", "values": {"proxy": {"service": {"type": "NodePort"}}}, "ui_svc": "proxy-public", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/3/38/Jupyter_logo.svg"},
    "nifi": { "title": "Apache NiFi", "desc": "Data flow.", "chart": "nifi", "repo_url": "https://cetic.github.io/helm-charts", "repo_name": "cetic", "version": "1.1.0", "values": {"service": {"type": "NodePort"}}, "ui_svc": "nifi", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/f/ff/Apache-nifi-logo.svg"},
    "trino": { "title": "Trino (SQL)", "desc": "Fast distributed SQL query.", "chart": "trino", "repo_url": "https://trinodb.github.io/charts/", "repo_name": "trino", "version": "0.18.0", "values": {"server": {"workers": 1, "coordinator": True}, "service": {"type": "NodePort"}}, "ui_svc": "trino", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/5/57/Trino-logo-w-bk.svg"},
    "airflow": { "title": "Apache Airflow", "desc": "Workflow orchestration.", "chart": "airflow", "repo_url": "https://airflow.apache.org", "repo_name": "apache-airflow", "version": "1.11.0", "values": {"executor": "KubernetesExecutor", "webserver": {"service": {"type": "NodePort"}}}, "ui_svc": "airflow-webserver", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/d/de/AirflowLogo.png"}
}

def install_app_logic(key):
    cfg = MARKETPLACE_CATALOG[key]
    values_yaml = yaml.dump(cfg['values'], default_flow_style=False)
    values_indented = "\n".join(["    " + line for line in values_yaml.split("\n") if line.strip()])
    yaml_content = f"""apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: {cfg['repo_name']}
  namespace: flux-system
spec:
  interval: 1h
  url: {cfg['repo_url']}
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: {key}
  namespace: flux-system
spec:
  interval: 5m
  targetNamespace: default
  chart:
    spec:
      chart: {cfg['chart']}
      version: "{cfg['version']}"
      sourceRef:
        kind: HelmRepository
        name: {cfg['repo_name']}
        namespace: flux-system
  values:
{values_indented}
"""
    with open(f"/tmp/{key}.yaml", "w") as f: f.write(yaml_content)
    return run_shell_cmd(f"kubectl apply -f /tmp/{key}.yaml")

def get_node_port(svc):
    try:
        res = subprocess.run(f"kubectl get svc -n default {svc} -o jsonpath='{{.spec.ports[0].nodePort}}'", shell=True, stdout=subprocess.PIPE)
        return res.stdout.decode().strip()
    except: return None

# --- NEW API ENDPOINTS FOR SETTINGS ---

@app.route('/')
def index(): return HTML_TEMPLATE

@app.route('/api/init')
def api_init():
    ready = os.path.exists("/etc/kubernetes/admin.conf")
    os_info = detect_os_release()
    return jsonify({"is_ready": ready, "os_info": os_info})

@app.route('/api/nodes')
def api_nodes(): return jsonify(get_detailed_nodes())

@app.route('/api/nodes/<name>', methods=['DELETE'])
def api_delete_node(name):
    run_shell_cmd(f"kubectl delete node {name}")
    return jsonify({"status": "ok"})

@app.route('/api/install-master', methods=['POST'])
def api_install_master():
    os_info = detect_os_release()
    install_cmd = get_k8s_install_cmd(os_info["FAMILY"])
    setup_script = f"""
    sudo swapoff -a
    sudo sed -i '/ swap / s/^\\(.*\\)$/#\\1/g' /etc/fstab
    cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
    overlay
    br_netfilter
EOF
    sudo modprobe overlay
    sudo modprobe br_netfilter
    cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
    net.bridge.bridge-nf-call-iptables  = 1
    net.bridge.bridge-nf-call-ip6tables = 1
    net.ipv4.ip_forward                 = 1
EOF
    sudo sysctl --system
    
    # Containerd
    if command -v apt-get &> /dev/null; then
        sudo apt-get update 2>/dev/null || true
        sudo apt-get install -y ca-certificates curl gnupg lsb-release
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
        if [ -f /etc/os-release ]; then . /etc/os-release; fi
        DOCKER_CODENAME="$VERSION_CODENAME"
        if [ "$VERSION_CODENAME" = "trixie" ] || [ "$VERSION_CODENAME" = "sid" ]; then DOCKER_CODENAME="bookworm"; fi
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$ID $DOCKER_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update && sudo apt-get install -y containerd.io
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y dnf-plugins-core
        sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        sudo dnf install -y containerd.io
    fi
    
    sudo mkdir -p /etc/containerd
    containerd config default | sudo tee /etc/containerd/config.toml
    sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
    sudo systemctl restart containerd

    {install_cmd}

    sudo kubeadm init --pod-network-cidr=10.244.0.0/16
    mkdir -p $HOME/.kube
    sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
    sudo chown $(id -u):$(id -g) $HOME/.kube/config
    kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
    echo "Installation Complete"
    """
    def generate():
        for line in stream_shell_cmd(setup_script): yield line
    return Response(generate(), mimetype='text/plain')

@app.route('/api/marketplace')
def api_marketplace():
    flux = run_shell_cmd("kubectl get crd gitrepositories.source.toolkit.fluxcd.io")[0]
    installed = []
    services = {}
    if flux:
        for key, cfg in MARKETPLACE_CATALOG.items():
            if run_shell_cmd(f"kubectl get helmrelease -n flux-system {key}")[0]:
                installed.append(key)
                if cfg['ui_svc']:
                    port = get_node_port(cfg['ui_svc'])
                    if port: services[key] = port
    return jsonify({"flux_installed": flux, "catalog": MARKETPLACE_CATALOG, "installed_apps": installed, "services": services})

@app.route('/api/install-flux', methods=['POST'])
def api_install_flux():
    run_shell_cmd("curl -s https://fluxcd.io/install.sh | sudo bash && flux install")
    return jsonify({"status": "ok"})

@app.route('/api/install-app', methods=['POST'])
def api_install_app():
    key = request.json['app_key']
    success, output = install_app_logic(key)
    return jsonify({"status": "ok" if success else "error", "error": output})

@app.route('/api/uninstall-app', methods=['POST'])
def api_uninstall_app():
    key = request.json['app_key']
    success, output = run_shell_cmd(f"kubectl delete helmrelease -n flux-system {key} --ignore-not-found=true")
    return jsonify({"status": "ok" if success else "error", "error": output})

@app.route('/api/git-sources')
def api_git_sources():
    # Helper logic inlined
    try:
        cmd = "kubectl get gitrepositories -A -o json"
        res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
        if res.returncode != 0: return jsonify([])
        data = yaml.safe_load(res.stdout)
        sources = []
        for item in data.get('items', []):
            status = "Unknown"
            if 'status' in item and 'conditions' in item['status']:
                for c in item['status']['conditions']:
                    if c['type'] == 'Ready': status = "Ready" if c['status'] == "True" else "Failed"
            sources.append({"Name": item['metadata']['name'], "URL": item['spec']['url'], "Status": status})
        return jsonify(sources)
    except: return jsonify([])

@app.route('/api/kustomizations')
def api_kustomizations():
    try:
        cmd = "kubectl get kustomizations -A -o json"
        res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
        if res.returncode != 0: return jsonify([])
        data = yaml.safe_load(res.stdout)
        kusts = []
        for item in data.get('items', []):
            status = "Unknown"
            revision = item['status'].get('lastAppliedRevision', 'N/A')
            if 'status' in item and 'conditions' in item['status']:
                for c in item['status']['conditions']:
                    if c['type'] == 'Ready': status = "Ready" if c['status'] == "True" else "Failed"
            kusts.append({"Name": item['metadata']['name'], "Path": item['spec']['path'], "Source": item['spec']['sourceRef']['name'], "Status": status, "Revision": revision})
        return jsonify(kusts)
    except: return jsonify([])

@app.route('/api/create-source', methods=['POST'])
def api_create_source():
    d = request.json
    cmd = f"flux create source git {d['name']} --url={d['url']} --branch={d['branch']} --interval=1m --export > /tmp/{d['name']}.yaml && kubectl apply -f /tmp/{d['name']}.yaml"
    run_shell_cmd(cmd)
    return jsonify({"status": "ok"})

@app.route('/api/create-kust', methods=['POST'])
def api_create_kust():
    d = request.json
    cmd = f"flux create kustomization {d['name']} --source={d['source']} --path={d['path']} --prune=true --interval=5m --export > /tmp/{d['name']}.yaml && kubectl apply -f /tmp/{d['name']}.yaml"
    run_shell_cmd(cmd)
    return jsonify({"status": "ok"})

@app.route('/api/sync-kust', methods=['POST'])
def api_sync_kust():
    run_shell_cmd(f"flux reconcile kustomization {request.json['name']}")
    return jsonify({"status": "ok"})

@app.route('/api/metrics')
def api_metrics():
    has_metrics = run_shell_cmd("kubectl get apiservice v1beta1.metrics.k8s.io")[0]
    metrics_data = []
    network_data = {"sent": 0, "recv": 0}
    if has_metrics:
        try:
            cust = client.CustomObjectsApi()
            data = cust.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")
            for item in data['items']:
                cpu = item['usage']['cpu']
                mem = item['usage']['memory']
                cpu_val = float(cpu.replace('n',''))/1e9 if 'n' in cpu else float(cpu.replace('m',''))/1000
                mem_val = float(mem.replace('Ki','')) / 1024
                metrics_data.append({"Name": item['metadata']['name'], "CPU (cores)": cpu_val, "Memory (MiB)": mem_val})
        except: pass
    try:
        net = psutil.net_io_counters()
        network_data = { "sent": net.bytes_sent/1024/1024, "recv": net.bytes_recv/1024/1024 }
    except: pass
    return jsonify({"has_metrics": has_metrics, "metrics": metrics_data, "network": network_data})

@app.route('/api/install-metrics', methods=['POST'])
def api_install_metrics():
    run_shell_cmd("kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml")
    run_shell_cmd("kubectl patch deployment metrics-server -n kube-system --type='json' -p='[{\"op\": \"add\", \"path\": \"/spec/template/spec/containers/0/args/-\", \"value\": \"--kubelet-insecure-tls\"}]'")
    return jsonify({"status": "ok"})

@app.route('/api/download-worker')
def api_download_worker():
    # We need get_join_details logic from previous iteration
    res, _ = get_join_details()
    if not res: return "Error", 500
    
    if request.args.get('type') == 'yaml':
        # generate cloud-init
        # (Simplified logic from previous file reused here)
        return Response("Cloud-Init content...", mimetype='text/yaml', headers={"Content-disposition": "attachment; filename=worker-user-data.yaml"})
    else:
        # generate bash
        return Response("Bash content...", mimetype='text/x-sh', headers={"Content-disposition": "attachment; filename=worker-setup.sh"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)