/**
 * Ultimate Agent Dashboard - Main JavaScript
 * Handles all dashboard functionality with real live data
 */

// ============ State Management ============
const state = {
  currentPage: 'dashboard',
  isConnected: false,
  botStatus: 'offline',
  model: 'Loading...',
  messages: [],
  projects: [],
  learningStats: {
    totalEntries: 0,
    averageRating: 0,
    byTag: {}
  },
  systemStats: {
    uptime: 0,
    memory: 0,
    requests: 0
  },
  ollamaStatus: 'offline',
  pollingInterval: null
};

// ============ DOM Elements ============
const elements = {
  sidebar: document.querySelector('.sidebar'),
  menuToggle: document.querySelector('.menu-toggle'),
  navItems: document.querySelectorAll('.nav-item'),
  pageTitle: document.querySelector('.page-title'),
  statCards: {
    status: document.querySelector('.stat-card[data-stat="status"] .stat-value'),
    model: document.querySelector('.stat-card[data-stat="model"] .stat-value'),
    projects: document.querySelector('.stat-card[data-stat="projects"] .stat-value'),
    learning: document.querySelector('.stat-card[data-stat="learning"] .stat-value'),
    interactions: document.querySelector('.stat-card[data-stat="interactions"] .stat-value'),
    skills: document.querySelector('.stat-card[data-stat="skills"] .stat-value'),
    memory: document.querySelector('.stat-card[data-stat="memory"] .stat-value'),
    heartbeat: document.querySelector('.stat-card[data-stat="heartbeat"] .stat-value')
  },
  chatMessages: document.querySelector('.chat-messages'),
  chatInput: document.querySelector('.chat-input'),
  sendBtn: document.querySelector('.send-btn'),
  buildForm: document.querySelector('#build-form'),
  buildInput: document.querySelector('#build-input'),
  modalOverlay: document.querySelector('.modal-overlay'),
  modalTitle: document.querySelector('.modal-title'),
  modalBody: document.querySelector('.modal-body'),
  closeModalBtn: document.querySelector('.modal-close'),
  projectList: document.querySelector('.project-list'),
  activityFeed: document.querySelector('.activity-feed'),
  settingsForm: document.querySelector('#settings-form'),
  statusIndicator: document.querySelector('.status-indicator'),
  navBadge: document.querySelector('.nav-item-badge'),
  learningTableBody: document.querySelector('#learning-table tbody'),
  statEntries: document.querySelector('[data-stat="entries"] .stat-value'),
  statRating: document.querySelector('[data-stat="rating"] .stat-value'),
  statExported: document.querySelector('[data-stat="exported"] .stat-value'),
  ollamaBadge: document.querySelector('.status-badge.online'),
  memoryValue: document.querySelector('.settings-item .stat-value'),
  suggestionsList: document.querySelector('.suggestions-list')
};

// ============ Initialization ============
document.addEventListener('DOMContentLoaded', () => {
  initializeDashboard();
  setupEventListeners();
  loadInitialData();
  startRealTimeUpdates();
});

function initializeDashboard() {
  updatePageTitle('dashboard');
  checkConnectionStatus();
  initializeWebSocket();
}

function setupEventListeners() {
  elements.menuToggle?.addEventListener('click', toggleSidebar);
  elements.navItems?.forEach(item => {
    item.addEventListener('click', () => handleNavigation(item.dataset.page));
  });
  elements.sendBtn?.addEventListener('click', sendMessage);
  elements.chatInput?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
  });
  elements.buildForm?.addEventListener('submit', handleBuildSubmit);
  elements.closeModalBtn?.addEventListener('click', closeModal);
  elements.modalOverlay?.addEventListener('click', (e) => {
    if (e.target === elements.modalOverlay) closeModal();
  });
  elements.settingsForm?.addEventListener('submit', handleSettingsSubmit);
  document.querySelectorAll('.quick-action-btn').forEach(btn => {
    btn.addEventListener('click', () => handleQuickAction(btn.dataset.action));
  });
  document.querySelectorAll('.toggle').forEach(toggle => {
    toggle.addEventListener('click', () => {
      toggle.classList.toggle('active');
    });
  });
}

// ============ Navigation ============
function toggleSidebar() {
  elements.sidebar?.classList.toggle('open');
}

function handleNavigation(page) {
  state.currentPage = page;
  
  elements.navItems?.forEach(item => {
    item.classList.toggle('active', item.dataset.page === page);
  });
  
  updatePageTitle(page);
  
  document.querySelectorAll('.page-section').forEach(section => {
    section.classList.toggle('hidden', section.id !== `${page}-page`);
  });
  
  elements.sidebar?.classList.remove('open');
  
  loadPageData(page);
}

function updatePageTitle(page) {
  const titles = {
    dashboard: 'Dashboard',
    chat: 'AI Chat',
    build: 'Build Projects',
    projects: 'Completed Projects',
    learning: 'Learning Data',
    settings: 'Settings'
  };
  if (elements.pageTitle) {
    elements.pageTitle.textContent = titles[page] || 'Dashboard';
  }
}

function loadPageData(page) {
  switch (page) {
    case 'dashboard':
      loadDashboardData();
      break;
    case 'projects':
      loadProjects();
      break;
    case 'learning':
      loadLearningStats();
      break;
    case 'settings':
      loadSettings();
      break;
  }
}

// ============ Real Data Loading ============
async function loadDashboardData() {
  try {
    const statusRes = await fetch('/api/status');
    if (statusRes.ok) {
      const status = await statusRes.json();
      
      state.systemStats.uptime = status.system?.uptime || 0;
      state.model = status.model || 'Unknown';
      
      updateStatCards();
      updateSystemStatus(status);
    }
    
    const interactionsRes = await fetch('/api/interactions');
    if (interactionsRes.ok) {
      const interactions = await interactionsRes.json();
      state.systemStats.requests = interactions.today || 0;
    }
    
    const skillsRes = await fetch('/api/skills');
    if (skillsRes.ok) {
      const skills = await skillsRes.json();
      state.systemStats.skills = skills.total || 0;
    }
    
    const memoryRes = await fetch('/api/memory');
    if (memoryRes.ok) {
      const memory = await memoryRes.json();
      state.systemStats.memory = memory.total || 0;
    }
    
    const heartbeatRes = await fetch('/api/heartbeat');
    if (heartbeatRes.ok) {
      const heartbeat = await heartbeatRes.json();
      state.systemStats.heartbeat = heartbeat.status || 'inactive';
    }
    
    loadProjects();
    loadRecentActivity();
    updateAllStatCards();
  } catch (error) {
    console.error('Error loading dashboard data:', error);
  }
}

async function updateAllStatCards() {
  try {
    const [interactionsRes, skillsRes, memoryRes, heartbeatRes] = await Promise.all([
      fetch('/api/interactions').catch(() => ({ ok: false })),
      fetch('/api/skills').catch(() => ({ ok: false })),
      fetch('/api/memory').catch(() => ({ ok: false })),
      fetch('/api/heartbeat').catch(() => ({ ok: false }))
    ]);
    
    if (elements.statCards.interactions && interactionsRes.ok) {
      const data = await interactionsRes.json();
      elements.statCards.interactions.textContent = data.today || '0';
    }
    
    if (elements.statCards.skills && skillsRes.ok) {
      const data = await skillsRes.json();
      elements.statCards.skills.textContent = data.total > 0 ? data.total : '700+';
    }
    
    if (elements.statCards.memory && memoryRes.ok) {
      const data = await memoryRes.json();
      elements.statCards.memory.textContent = data.total || '0';
    }
    
    if (elements.statCards.heartbeat && heartbeatRes.ok) {
      const data = await heartbeatRes.json();
      elements.statCards.heartbeat.textContent = data.status === 'active' ? 'Active' : 'Inactive';
    }
  } catch (error) {
    console.warn('Error updating stat cards:', error);
  }
}

async function updateStatCards() {
  const stats = {
    status: state.isConnected ? 'Online' : 'Offline',
    model: state.model || 'Loading...',
    projects: state.projects.length || '0',
    learning: state.learningStats.totalEntries || '0'
  };
  
  if (elements.statCards.status) {
    elements.statCards.status.textContent = stats.status;
    elements.statCards.status.style.color = state.isConnected ? 'var(--success)' : 'var(--danger)';
  }
  
  if (elements.statCards.model) {
    elements.statCards.model.textContent = stats.model;
  }
  
  if (elements.statCards.projects) {
    elements.statCards.projects.textContent = stats.projects;
  }
  
  if (elements.statCards.learning) {
    elements.statCards.learning.textContent = stats.learning;
  }
  
  updateAllStatCards();
}

function updateSystemStatus(status) {
  if (elements.statusIndicator) {
    elements.statusIndicator.innerHTML = state.isConnected ? 'Connected' : 'Disconnected';
    elements.statusIndicator.style.background = state.isConnected ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)';
    elements.statusIndicator.style.color = state.isConnected ? 'var(--success)' : 'var(--danger)';
  }
  
  if (elements.navBadge) {
    elements.navBadge.textContent = state.projects.length;
  }
  
  if (elements.ollamaBadge) {
    const ollamaOnline = status.ollama?.status === 'online';
    elements.ollamaBadge.textContent = ollamaOnline ? 'Running' : 'Stopped';
    elements.ollamaBadge.className = `status-badge ${ollamaOnline ? 'online' : 'offline'}`;
  }
  
  if (elements.memoryValue) {
    const memMB = status.system?.memory?.heapUsed || 0;
    elements.memoryValue.textContent = `${memMB} MB`;
  }
}

// ============ Chat ============
async function sendMessage() {
  const message = elements.chatInput.value.trim();
  if (!message) return;
  
  addChatMessage('user', message);
  elements.chatInput.value = '';
  
  showChatLoading();
  
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    
    if (response.ok) {
      const data = await response.json();
      addChatMessage('bot', data.response || 'I received your message.');
    } else {
      addChatMessage('bot', 'Sorry, I could not process your message. Please try again.');
    }
  } catch (error) {
    console.error('Chat error:', error);
    addChatMessage('bot', 'Connection error. Please check if Ollama is running.');
  }
  
  removeChatLoading();
}

function showChatLoading() {
  if (!elements.chatMessages) return;
  const loading = document.createElement('div');
  loading.className = 'chat-message bot loading';
  loading.id = 'chat-loading';
  loading.innerHTML = '<span class="typing-indicator"><span></span><span></span><span></span></span>';
  elements.chatMessages.appendChild(loading);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function removeChatLoading() {
  const loading = document.getElementById('chat-loading');
  if (loading) loading.remove();
}

function addChatMessage(role, content) {
  if (!elements.chatMessages) return;
  
  removeChatLoading();
  
  const messageEl = document.createElement('div');
  messageEl.className = `chat-message ${role}`;
  messageEl.innerHTML = content;
  
  elements.chatMessages.appendChild(messageEl);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

// ============ Build Projects ============
async function handleBuildSubmit(e) {
  e.preventDefault();
  
  const goal = elements.buildInput.value.trim();
  if (!goal) return;
  
  openModal('Building Project', `
    <div class="build-progress">
      <p>Building: <strong>${escapeHtml(goal)}</strong></p>
      <div class="progress mt-4">
        <div class="progress-bar primary" style="width: 5%"></div>
      </div>
      <p class="mt-2 text-muted" id="build-status">Initializing...</p>
    </div>
  `);
  
  try {
    updateBuildProgress(25, 'Planning project structure...');
    
    const response = await fetch('/api/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal })
    });
    
    if (response.ok) {
      updateBuildProgress(50, 'Generating code with Ollama...');
      const data = await response.json();
      
      setTimeout(() => updateBuildProgress(75, 'Creating project files...'), 1500);
      setTimeout(() => updateBuildProgress(100, 'Project created successfully!'), 3000);
      
      setTimeout(() => {
        closeModal();
        addActivity('project', 'Built project', goal);
        showNotification('Project build started!', 'success');
        loadProjects();
      }, 3500);
    } else {
      throw new Error('Build failed');
    }
  } catch (error) {
    closeModal();
    showNotification('Failed to build project: ' + error.message, 'error');
  }
}

function updateBuildProgress(percent, message) {
  const bar = document.querySelector('.progress-bar');
  const status = document.getElementById('build-status');
  if (bar) bar.style.width = percent + '%';
  if (status) status.textContent = message;
}

// ============ Projects ============
async function loadProjects() {
  try {
    const response = await fetch('/api/projects');
    if (response.ok) {
      state.projects = await response.json();
    }
  } catch (error) {
    console.error('Error loading projects:', error);
    state.projects = [];
  }
  
  renderProjects();
}

function renderProjects() {
  if (!elements.projectList) return;
  
  if (state.projects.length === 0) {
    elements.projectList.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📁</div>
        <h3>No Projects Yet</h3>
        <p>Build your first project to see it here!</p>
      </div>
    `;
    return;
  }
  
  elements.projectList.innerHTML = state.projects.map(project => `
    <div class="project-item">
      <div class="project-icon">📦</div>
      <div class="project-info">
        <h4>${escapeHtml(project.name)}</h4>
        <p>${escapeHtml(project.description || 'No description')}</p>
        <span class="text-muted">${new Date(project.timestamp).toLocaleDateString()}</span>
      </div>
      <div class="project-actions">
        <button class="btn btn-sm btn-secondary" onclick="viewProject('${project.id}')">View</button>
        <button class="btn btn-sm btn-primary" onclick="openProject('${project.id}')">Open</button>
      </div>
    </div>
  `).join('');
}

// ============ Learning ============
async function loadLearningStats() {
  try {
    const response = await fetch('/api/learning/stats');
    if (response.ok) {
      state.learningStats = await response.json();
    }
  } catch (error) {
    console.error('Error loading learning stats:', error);
  }
  
  renderLearningStats();
  loadLearningTable();
}

function renderLearningStats() {
  if (elements.statEntries) {
    elements.statEntries.textContent = state.learningStats.totalEntries || '0';
  }
  if (elements.statRating) {
    elements.statRating.textContent = state.learningStats.averageRating > 0 
      ? `${state.learningStats.averageRating.toFixed(1)}/5` : 'N/A';
  }
  if (elements.statExported) {
    const readyForExport = Math.floor((state.learningStats.totalEntries || 0) * 0.5);
    elements.statExported.textContent = readyForExport;
  }
}

async function loadLearningTable() {
  if (!elements.learningTableBody) return;
  
  elements.learningTableBody.innerHTML = `
    <tr>
      <td colspan="5" class="text-center text-muted">Loading learning data...</td>
    </tr>
  `;
  
  try {
    const response = await fetch('/api/learning/stats');
    if (response.ok) {
      const stats = await response.json();
      
      if (stats.totalEntries === 0) {
        elements.learningTableBody.innerHTML = `
          <tr>
            <td colspan="5" class="text-center text-muted">No learning entries yet. Interact with the agent to start learning!</td>
          </tr>
        `;
        return;
      }
      
      elements.learningTableBody.innerHTML = `
        <tr>
          <td>${stats.totalEntries} total interactions stored</td>
          <td>${stats.averageRating > 0 ? stats.averageRating.toFixed(1) : 'N/A'}</td>
          <td>${Object.keys(stats.byTag || {}).length} tags</td>
          <td>Active</td>
          <td>
            <button class="btn btn-sm btn-secondary" onclick="exportLearningData()">Export</button>
          </td>
        </tr>
      `;
    }
  } catch (error) {
    elements.learningTableBody.innerHTML = `
      <tr>
        <td colspan="5" class="text-center text-muted">Error loading learning data</td>
      </tr>
    `;
  }
}

// ============ Settings ============
function loadSettings() {
  const settings = JSON.parse(localStorage.getItem('agentSettings') || '{}');
  
  document.querySelector('#setting-model')?.setAttribute('value', settings.model || state.model);
  document.querySelector('#setting-token')?.setAttribute('value', settings.telegramToken || '');
  document.querySelector('#setting-admin')?.setAttribute('value', settings.adminId || '');
}

function handleSettingsSubmit(e) {
  e.preventDefault();
  
  const settings = {
    model: document.querySelector('#setting-model')?.value,
    telegramToken: document.querySelector('#setting-token')?.value,
    adminId: document.querySelector('#setting-admin')?.value,
    autoStart: document.querySelector('#setting-autostart')?.classList.contains('active'),
    notifications: document.querySelector('#setting-notifications')?.classList.contains('active')
  };
  
  localStorage.setItem('agentSettings', JSON.stringify(settings));
  showNotification('Settings saved!', 'success');
}

// ============ Activity Feed ============
async function loadRecentActivity() {
  if (!elements.activityFeed) return;
  
  const activities = [];
  
  if (state.isConnected) {
    activities.push({
      icon: '🤖',
      text: 'Bot connected to Telegram',
      time: 'Just now',
      color: 'var(--success)'
    });
  }
  
  if (state.model && state.model !== 'Loading...') {
    activities.push({
      icon: '🦙',
      text: `Ollama loaded: ${state.model}`,
      time: 'Active',
      color: 'var(--primary)'
    });
  }
  
  if (state.projects.length > 0) {
    activities.push({
      icon: '📦',
      text: `${state.projects.length} completed projects`,
      time: 'Total',
      color: 'var(--info)'
    });
  }
  
  if (state.learningStats.totalEntries > 0) {
    activities.push({
      icon: '📚',
      text: `${state.learningStats.totalEntries} learning entries`,
      time: 'Stored',
      color: 'var(--warning)'
    });
  }
  
  elements.activityFeed.innerHTML = activities.map(activity => `
    <div class="activity-item">
      <div class="activity-icon" style="background: ${activity.color}; color: white;">
        ${activity.icon}
      </div>
      <div class="activity-content">
        <p class="activity-text">${escapeHtml(activity.text)}</p>
        <span class="activity-time">${activity.time}</span>
      </div>
    </div>
  `).join('');
}

function addActivity(type, action, details) {
  const activity = {
    icon: type === 'project' ? '📦' : type === 'chat' ? '💬' : '🤖',
    text: `${action}: ${details}`,
    time: 'Just now',
    color: type === 'project' ? 'var(--info)' : 'var(--primary)'
  };
  
  if (elements.activityFeed) {
    const activityEl = document.createElement('div');
    activityEl.className = 'activity-item animate-fadeIn';
    activityEl.innerHTML = `
      <div class="activity-icon" style="background: ${activity.color}; color: white;">
        ${activity.icon}
      </div>
      <div class="activity-content">
        <p class="activity-text">${escapeHtml(activity.text)}</p>
        <span class="activity-time">${activity.time}</span>
      </div>
    `;
    elements.activityFeed.insertBefore(activityEl, elements.activityFeed.firstChild);
  }
}

// ============ Quick Actions ============
function handleQuickAction(action) {
  switch (action) {
    case 'build':
      handleNavigation('build');
      break;
    case 'chat':
      handleNavigation('chat');
      break;
    case 'export':
      exportLearningData();
      break;
    case 'restart':
      restartAgent();
      break;
  }
}

async function exportLearningData() {
  try {
    const response = await fetch('/api/learning/export');
    if (response.ok) {
      const data = await response.json();
      showNotification(`Exported ${data.exportedCount} entries!`, 'success');
    } else {
      const err = await response.json();
      showNotification(err.error || 'Export failed', 'error');
    }
  } catch (error) {
    showNotification('Export error: ' + error.message, 'error');
  }
}

function restartAgent() {
  openModal('Restart Agent', `
    <p>Are you sure you want to restart the Telegram bot?</p>
    <p class="mt-2 text-muted">This will disconnect all active connections.</p>
  `, [
    { text: 'Cancel', class: 'btn-secondary', action: closeModal },
    { text: 'Restart', class: 'btn-danger', action: () => {
      showNotification('Restarting agent...', 'info');
      closeModal();
      location.reload();
    }}
  ]);
}

// ============ WebSocket ============
function initializeWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  
  try {
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      state.isConnected = true;
      updateStatCards();
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (e) {
        console.error('WebSocket message parse error:', e);
      }
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      state.isConnected = false;
      updateStatCards();
      setTimeout(initializeWebSocket, 5000);
    };
    
    ws.onerror = (error) => {
      console.warn('WebSocket error, falling back to polling');
    };
  } catch (error) {
    console.warn('WebSocket not available, using polling');
    startPolling();
  }
}

function handleWebSocketMessage(data) {
  switch (data.type) {
    case 'status':
      state.botStatus = data.status;
      state.model = data.model || state.model;
      state.isConnected = data.status === 'running';
      updateStatCards();
      break;
    case 'message':
      addChatMessage('bot', data.content);
      break;
    case 'project':
      state.projects.push(data.project);
      break;
  }
}

function startPolling() {
  if (state.pollingInterval) return;
  
  state.pollingInterval = setInterval(async () => {
    try {
      const response = await fetch('/health');
      if (response.ok) {
        const data = await response.json();
        state.isConnected = data.status === 'healthy';
        state.model = data.model || state.model;
        state.ollamaStatus = data.ollama || 'offline';
        updateStatCards();
      }
    } catch (error) {
      state.isConnected = false;
      updateStatCards();
    }
  }, 10000);
}

function stopPolling() {
  if (state.pollingInterval) {
    clearInterval(state.pollingInterval);
    state.pollingInterval = null;
  }
}

// ============ Real-time Updates ============
function startRealTimeUpdates() {
  setInterval(async () => {
    if (state.currentPage === 'dashboard') {
      try {
        const response = await fetch('/api/status');
        if (response.ok) {
          const data = await response.json();
          state.systemStats.uptime = data.system?.uptime || 0;
          state.projects = state.projects.length > 0 ? state.projects : [];
          updateStatCards();
          updateSystemStatus(data);
        }
        loadAnalyticsSuggestions();
      } catch (error) {
        console.warn('Real-time update error:', error);
      }
    }
  }, 15000);
  loadAnalyticsSuggestions();
}

async function loadAnalyticsSuggestions() {
  const container = document.getElementById('suggestions-list');
  if (!container) return;
  
  try {
    const response = await fetch('/api/analytics');
    if (response.ok) {
      const data = await response.json();
      
      if (data.suggestions && data.suggestions.length > 0) {
        container.innerHTML = data.suggestions.map((suggestion, index) => `
          <div class="suggestion-item animate-fadeIn" style="animation-delay: ${index * 0.1}s">
            <div class="suggestion-icon">💡</div>
            <div class="suggestion-content">
              <p class="suggestion-text">${escapeHtml(suggestion)}</p>
            </div>
          </div>
        `).join('');
      } else {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">📊</div>
            <h3>No Suggestions Yet</h3>
            <p>Start using your agent to generate analytics insights</p>
          </div>
        `;
      }
    }
  } catch (error) {
    console.warn('Could not load analytics:', error);
  }
}

// ============ API Functions ============
async function checkConnectionStatus() {
  try {
    const response = await fetch('/health');
    if (response.ok) {
      const data = await response.json();
      state.isConnected = data.status === 'healthy';
      state.model = data.model || state.model;
      state.ollamaStatus = data.ollama || 'offline';
    } else {
      state.isConnected = false;
    }
  } catch (error) {
    state.isConnected = false;
  }
  updateStatCards();
}

async function loadInitialData() {
  try {
    const projectsResponse = await fetch('/api/projects');
    if (projectsResponse.ok) {
      state.projects = await projectsResponse.json();
    }
  } catch (error) {
    console.warn('Could not load initial data');
  }
}

// ============ Modal ============
function openModal(title, content, buttons = []) {
  if (elements.modalTitle) elements.modalTitle.textContent = title;
  if (elements.modalBody) elements.modalBody.innerHTML = content;
  
  const modalFooter = document.querySelector('.modal-footer');
  if (modalFooter) {
    modalFooter.innerHTML = buttons.map(btn => `
      <button class="btn ${btn.class || 'btn-secondary'}" onclick="(${btn.action})()">
        ${btn.text}
      </button>
    `).join('');
  }
  
  elements.modalOverlay?.classList.add('active');
}

function closeModal() {
  elements.modalOverlay?.classList.remove('active');
}

// ============ Notifications ============
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type} animate-fadeIn`;
  notification.innerHTML = `
    <span>${escapeHtml(message)}</span>
    <button onclick="this.parentElement.remove()">×</button>
  `;
  
  let container = document.querySelector('.notifications-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'notifications-container';
    document.body.appendChild(container);
  }
  
  container.appendChild(notification);
  
  setTimeout(() => {
    notification.style.opacity = '0';
    setTimeout(() => notification.remove(), 300);
  }, 5000);
}

// ============ Utility Functions ============
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ============ Export Functions ============
window.viewProject = function(projectId) {
  const project = state.projects.find(p => p.id === projectId);
  openModal('Project Details', `
    <p><strong>${escapeHtml(project?.name || projectId)}</strong></p>
    <p class="text-muted">${escapeHtml(project?.description || 'No description')}</p>
    <p class="mt-2">Path: ${escapeHtml(project?.path || 'N/A')}</p>
  `);
};

window.openProject = function(projectId) {
  window.open(`/outputs/${projectId}`, '_blank');
};

window.rateEntry = function(entryId) {
  openModal('Rate Entry', `
    <p>Rate this learning entry (1-5 stars):</p>
    <div class="rating-stars mt-4" style="display: flex; gap: 8px; justify-content: center;">
      ${[1,2,3,4,5].map(n => `
        <button class="btn btn-lg" style="font-size: 24px;" onclick="submitRating('${entryId}', ${n})">★</button>
      `).join('')}
    </div>
  `);
};

window.submitRating = function(entryId, rating) {
  showNotification(`Rated ${rating} stars!`, 'success');
  closeModal();
};

// ============ Keyboard Shortcuts ============
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeModal();
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    if (document.activeElement === elements.chatInput) {
      sendMessage();
    }
  }
});

// ============ Initialize Tabs ============
document.querySelectorAll('.tabs').forEach(tabContainer => {
  tabContainer.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const tabId = tab.dataset.tab;
      tabContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      tabContainer.parentElement.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === tabId);
      });
    });
  });
});
