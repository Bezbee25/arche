/* arche web UI - vanilla JS */
'use strict';

const API = '';  // Same origin

// -- State -----------------------------------------------------------------
const state = {
  plans: [],
  selectedPlanId: null,
  activeTab: 'tasks',
  consoleCollapsed: false,
  terminals: [],
  activeTerminalId: null,
  pollInterval: null,
  outputText: '',
  outputRunning: false,
  outputEventSource: null,
  _outputMeta: '',
  _outputDone: false,   // true after first __DONE__ received (prevents placeholder reset)
  _outputTerminal: null, // streaming terminal for generation operations
  editingTask: null,
  doneTask: null,
  blockTask: null,
  uiSelectedTaskId: null,   // task clicked in the UI (for actions)
  bulkSelectedTaskIds: [],  // tasks selected via checkboxes - preserves order
  taskFilter: 'all',        // 'all' | 'TODO' | 'SELECTED' | 'IN_PROGRESS' | 'DONE'
  runTask: null,            // { trackId, taskId } | null
  interview: null,          // { planId, description, qa, currentQuestion } | null
  reviewTask: null,         // { planId, taskId, verdict, issues } | null
  newPhasePlanId: null,
  addTaskTrackId: null,
  newTrackType: 'feature',
  collapsedPhases: new Set(), // phase IDs that are collapsed
  _userScrolling: null,     // id of tab where user is scrolling ('spec' | 'tasks' | 'output')
  _autoRefreshBlocked: false, // true if user is scrolling in any section
  hasPassword: false,       // whether a password is set
  sessionLocked: false,     // whether session is currently locked
  selectedInstructionIds: new Set(JSON.parse(localStorage.getItem('selectedInstructionIds') || '[]')), // instructions selectionnees (checkboxes)
  projectAgentsByPhase: {}, // agents per LLM phase (loaded from project.agents)
  specTaskCount: 0, // task count in active track (loaded at spec render)
  specPhaseCount: 0, // phase count in active track (loaded at spec render)
};

let _termCounter = 0;

// -- Utilities -------------------------------------------------------------
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// -- API helpers ------------------------------------------------------------
async function apiFetch(path, opts = {}) {
  try {
    const res = await fetch(API + path, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
    });
    if (!res.ok) {
      const body = await res.text();
      console.error(`API ${res.status} ${path}`, body);
      throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
  } catch (e) {
    console.error('API error', path, e);
    return null;
  }
}

const api = {
  saveSpec: (planId, content) => apiFetch(`/api/tracks/${planId}/spec`, { method: 'POST', body: JSON.stringify({ content }) }),
  getProject: () => apiFetch('/api/project'),
  getTracks: () => apiFetch('/api/tracks'),
  getActive: () => apiFetch('/api/tracks/active'),
  getTrack: (id) => apiFetch(`/api/tracks/${id}`),
  getTrackSpec: (id) => apiFetch(`/api/tracks/${id}/spec`),
  getSession: (trackId, date) => apiFetch(`/api/tracks/${trackId}/sessions/${date}`),
  getRunStatus: (trackId) => apiFetch(`/api/tracks/${trackId}/run-status`),
  createTrack: (name, trackType = 'feature') => apiFetch('/api/tracks', { method: 'POST', body: JSON.stringify({ name, track_type: trackType }) }),
  generateTemplate: (planId, description, subtypes) => apiFetch(`/api/tracks/${planId}/tasks/generate-template`, { method: 'POST', body: JSON.stringify({ description, subtypes }) }),
  switchTrack: (id) => apiFetch('/api/tracks/switch', { method: 'POST', body: JSON.stringify({ track_id: id }) }),
  doneTrack: (id) => apiFetch(`/api/tracks/${id}/done`, { method: 'POST' }),
  nextTask: (trackId) => apiFetch(`/api/tracks/${trackId}/tasks/next`, { method: 'POST' }),
  addTask: (trackId, title, phaseId = '', files = []) => apiFetch(`/api/tracks/${trackId}/tasks`, { method: 'POST', body: JSON.stringify({ title, phase_id: phaseId, files }) }),
  getTasks: (trackId) => apiFetch(`/api/tracks/${trackId}/tasks`),
  getTrackFiles: (trackId) => apiFetch(`/api/tracks/${trackId}/files`),
  setTrackFiles: (trackId, files) => apiFetch(`/api/tracks/${trackId}/files`, { method: 'PUT', body: JSON.stringify({ files }) }),
  doneTask: (trackId, taskId, notes = '') => apiFetch(`/api/tracks/${trackId}/tasks/done`, { method: 'POST', body: JSON.stringify({ task_id: taskId, notes }) }),
  blockTask: (trackId, taskId, reason) => apiFetch(`/api/tracks/${trackId}/tasks/block`, { method: 'POST', body: JSON.stringify({ task_id: taskId, reason }) }),
  selectTask: (trackId, taskId) => apiFetch(`/api/tracks/${trackId}/tasks/${taskId}/select`, { method: 'POST' }),
  updateTask: (trackId, taskId, updates) => apiFetch(`/api/tracks/${trackId}/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify(updates) }),
  reworkTask: (trackId, taskId, issues) => apiFetch(`/api/tracks/${trackId}/tasks/${taskId}/rework`, { method: 'POST', body: JSON.stringify({ review_issues: issues }) }),
  // Phases
  getPhases: (trackId) => apiFetch(`/api/tracks/${trackId}/phases`),
  createPhase: (trackId, name, desc, depends_on = []) => apiFetch(`/api/tracks/${trackId}/phases`, { method: 'POST', body: JSON.stringify({ name, description: desc, depends_on }) }),
  deletePhase: (trackId, phaseId) => apiFetch(`/api/tracks/${trackId}/phases/${phaseId}`, { method: 'DELETE' }),
  // Archi + Memory
  getArchi: () => apiFetch('/api/archi'),
  getMemory: () => apiFetch('/api/memory'),
  clearMemory: () => apiFetch('/api/memory', { method: 'DELETE' }),
  // Password lock
  getPasswordStatus: () => apiFetch('/api/settings/password'),
  setupPassword: (password) => apiFetch('/api/settings/password/setup', { method: 'POST', body: JSON.stringify({ password }) }),
  verifyPassword: (password) => apiFetch('/api/settings/password/verify', { method: 'POST', body: JSON.stringify({ password }) }),
  updatePassword: (password) => apiFetch('/api/settings/password', { method: 'PATCH', body: JSON.stringify({ password }) }),
  clearPassword: () => apiFetch('/api/settings/password/clear', { method: 'POST' }),
  getJiraSettings: () => apiFetch('/api/settings/jira'),
  // Jira
  importEpic: (epicKey) => apiFetch('/api/jira/import-epic', { method: 'POST', body: JSON.stringify({ epic_key: epicKey }) }),
  validateJql: (jql) => apiFetch('/api/jira/validate-jql', { method: 'POST', body: JSON.stringify({ jql }) }),
  importJql: (jql, trackName) => apiFetch('/api/jira/jql-import', { method: 'POST', body: JSON.stringify({ jql, track_name: trackName }) }),
  // Agents
  listAgents: () => apiFetch('/api/agents'),
  getAgent: (id) => apiFetch(`/api/agents/${id}`),
  createAgent: (data) => apiFetch('/api/agents', { method: 'POST', body: JSON.stringify(data) }),
  updateAgent: (id, data) => apiFetch(`/api/agents/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteAgent: (id) => apiFetch(`/api/agents/${id}`, { method: 'DELETE' }),
  // Instructions
  getInstructions: () => apiFetch('/api/instructions/list'),
  searchInstructions: (params) => {
    const query = new URLSearchParams(params).toString();
    return apiFetch(`/api/instructions/search?${query}`);
  },
  getInstruction: (id) => apiFetch(`/api/instructions/get?id=${id}`),
  getUserInstructions: () => apiFetch('/api/instructions/store/list'),
  searchUserInstructions: (params) => {
    const query = new URLSearchParams(params).toString();
    return apiFetch(`/api/instructions/store/search?${query}`);
  },
  getUserInstruction: (id) => apiFetch(`/api/instructions/store/get/${id}`),
  addUserInstruction: (instruction) => apiFetch('/api/instructions/store/add', { method: 'POST', body: JSON.stringify(instruction) }),
  updateUserInstruction: (instruction) => apiFetch('/api/instructions/store/update', { method: 'PUT', body: JSON.stringify(instruction) }),
  deleteUserInstruction: (id) => apiFetch(`/api/instructions/store/delete/${id}`, { method: 'DELETE' }),
  enableUserInstruction: (id, enabled) => apiFetch(`/api/instructions/store/enable/${id}`, { method: 'POST', body: JSON.stringify({ enabled }) }),
};

// -- DOM refs ---------------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const $id = (id) => document.getElementById(id);
const escapeHtml = (s) => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

// -- Scroll detection helpers ------------------------------------------------
function setupScrollDetection() {
  // Detect user scrolling in spec and tasks tabs (output is now in terminals section)
  ['tab-spec', 'tasks-scroll'].forEach(id => {
    const el = $id(id);
    if (!el) return;

    let scrollTimeout = null;
    el.addEventListener('scroll', () => {
      state._autoRefreshBlocked = true;
      state._userScrolling = id;

      // Clear existing timeout
      if (scrollTimeout) clearTimeout(scrollTimeout);

      // Resume auto-refresh 5 seconds after user stops scrolling
      scrollTimeout = setTimeout(() => {
        state._autoRefreshBlocked = false;
        state._userScrolling = null;
        scrollTimeout = null;
      }, 5000);
    }, { passive: true });
  });
}


// -- Init -------------------------------------------------------------------
async function init() {
  setupResizableConsole();
  setupEventListeners();  // registers theme listeners synchronously
  try { setupTerminal(); } catch (e) { console.error('Terminal init failed', e); }
  // Fetch project and apply server-side saved theme
  const project = await api.getProject();
  setupTheme(project ? (project.name || 'default') : 'default');
  // Override with server-persisted theme (takes priority over localStorage)
  try {
    const ts = await apiFetch('/api/settings/theme');
    if (ts && ts.theme) applyTheme(ts.theme);
  } catch (_) {}
  state.projectAgentsByPhase = (project && project.agents) ? project.agents : {};
  await refresh();
  // Force le rendu initial du panel (refresh() skippe le panel si rien ne tourne)
  if (state.selectedPlanId) {
    await renderPanelFor(state.selectedPlanId);
  } else if (state.plans.length > 0) {
    state.selectedPlanId = state.plans[0].id;
    await renderPanelFor(state.plans[0].id);
  }
  setupScrollDetection();
  updateInstructionSelectionFeedback();
  updateJiraButtonState();
  // Setup lock screen on page load
  await setupLockScreen();
  // Listen for lock state changes from other tabs
  setupLockStorageSync();
  startPolling();
}

async function refresh() {
  const [project, plans] = await Promise.all([api.getProject(), api.getTracks()]);
  if (project) {
    $id('project-name').textContent = project.name || 'unknown project';
    state.projectAgentsByPhase = project.agents || {};
  }
  if (plans) {
    state.plans = plans;
    renderSidebar(plans);

    // Auto-select active plan
    const activePlan = plans.find(p => p.status === 'ACTIVE');
    if (activePlan && !state.selectedPlanId) {
      state.selectedPlanId = activePlan.id;
    }

    // Re-render the panel only if a task is running (avoids display flicker)
    if (!state.outputRunning) return;

    // Skip panel re-render if user is scrolling or has a dropdown open
    if (state._autoRefreshBlocked) return;
    if (document.activeElement?.matches('.task-inline-status, .task-inline-type')) return;

    if (state.selectedPlanId) {
      await renderPanelFor(state.selectedPlanId);
    } else if (plans.length > 0) {
      state.selectedPlanId = plans[0].id;
      await renderPanelFor(plans[0].id);
    } else {
      renderEmptyPanel();
    }
  }
}

function startPolling() {
  state.pollInterval = setInterval(refresh, 3000);
}

// -- Sidebar ----------------------------------------------------------------
function renderSidebar(plans) {
  const container = $id('plan-list');
  if (plans.length === 0) {
    container.innerHTML = '<div class="empty-state">No tracks yet</div>';
    return;
  }

  container.innerHTML = plans.map(p => {
    const stats = p.stats || {};
    const done = stats.DONE || 0;
    const total = stats.total || 0;
    const pct = total > 0 ? Math.round(done / total * 100) : 0;
    const status = (p.status || 'PAUSED').toLowerCase();
    const isSelected = p.id === state.selectedPlanId;

    return `
      <div class="plan-item ${status} ${isSelected ? 'active' : ''}" data-id="${p.id}">
        <div class="plan-item-name">${escHtml(p.name || p.id)}</div>
        <div class="plan-item-meta">
          <span class="badge badge-${status}">${p.status}</span>
          <span>${done}/${total}</span>
        </div>
        <div class="plan-progress-bar">
          <div class="plan-progress-fill" style="width:${pct}%"></div>
        </div>
      </div>`;
  }).join('');

  // Bind click
  container.querySelectorAll('.plan-item').forEach(el => {
    el.addEventListener('click', async () => {
      const id = el.dataset.id;
      state.selectedPlanId = id;
      // Update sidebar selection visually
      container.querySelectorAll('.plan-item').forEach(e => e.classList.remove('active'));
      el.classList.add('active');
      // Close instructions/agents panel if open
      if ($id('instructions-panel').classList.contains('visible')) {
        toggleInstructionsView(false);
      }
      if ($id('agents-panel').classList.contains('visible')) {
        toggleAgentsView(false);
      }
      await renderPanelFor(id);
    });
  });
}

// -- Panel ------------------------------------------------------------------
async function renderPanelFor(planId) {
  const plan = await api.getTrack(planId);
  if (!plan) return;

  // Save editor state for previous track, restore for the new one
  if (state._lastPlan && state._lastPlan.id !== planId) {
    _saveEditorStateForTrack(state._lastPlan.id);
    _restoreEditorStateForTrack(planId);
    if ($id('editor-tab-bar')) { _renderTabBar(); _renderEditorHeaderActions(); }
  }

  state._lastPlan = plan;
  renderPlanHeader(plan);

  // Restore outputRunning state if there's an active run
  const runStatus = await api.getRunStatus(planId);
  if (runStatus && runStatus.running) {
    state.outputRunning = true;
  }

  renderTabContent(plan, state.activeTab);
}

function renderEmptyPanel() {
  $id('plan-header').innerHTML = '<div class="empty-state" style="padding:32px">No track selected</div>';
  $id('tab-tasks').innerHTML = '';
  $id('tab-spec').innerHTML = '';
  $id('tab-sessions').innerHTML = '';
}

function renderPlanHeader(plan) {
  const stats = plan.stats || {};
  const done = stats.DONE || 0;
  const total = stats.total || 0;
  const phase = plan.phase || 'spec';
  const status = (plan.status || '').toLowerCase();
  const pct = total > 0 ? Math.round(done / total * 100) : 0;

  $id('plan-header').innerHTML = `
    <div class="plan-header-row1">
      <div class="plan-header-title">${escHtml(plan.name || plan.id)}</div>
      <div id="plan-header-actions"></div>
    </div>
    <div class="plan-header-meta">
      <span class="badge badge-${status}">${plan.status || ''}</span>
      <span class="phase-tag phase-${phase}">${phase.toUpperCase()}</span>
      <span>${done}/${total} tasks</span>
      <span style="display:flex;align-items:center">
        <div class="plan-progress-bar" style="margin:0;width:80px">
          <div class="plan-progress-fill" style="width:${pct}%"></div>
        </div>
      </span>
      ${plan.status !== 'ACTIVE' && plan.status !== 'DONE' ? `<button class="btn-blue" onclick="switchToPlan('${plan.id}')">Activate</button>` : ''}
      ${plan.status === 'ACTIVE' ? `<button class="btn-ghost btn-sm btn-danger-ghost" onclick="confirmDoneTrack('${plan.id}')">✓ Track done</button>` : ''}
    </div>`;
}

async function renderTabContent(plan, tab) {
  switch (tab) {
    case 'tasks': renderTasks(plan); break;
    case 'spec': await renderSpec(plan.id); break;
    case 'sessions': renderSessions(plan); break;
    case 'output': renderOutputPane(); break;
    case 'editor': await renderEditor(); break;
  }
}

// -- Tasks tab --------------------------------------------------------------
const TASK_ICONS = { DONE: '✓', IN_PROGRESS: '▶', TODO: '·', BLOCKED: '✗' };
const TASK_LABELS = { IN_PROGRESS: 'IN PROGRESS', BLOCKED: 'BLOCKED' };

function renderTasks(plan) {
  const phases = plan.phases || [];
  const usePhases = phases.length > 1 || (phases.length === 1 && phases[0].name);

  if (usePhases) {
    renderTasksWithPhases(plan, phases);
    return;
  }

  const allTasks = plan.tasks || [];
  const stats = plan.stats || {};
  const planId = plan.id;
  const pane = $id('tab-tasks');

  if (allTasks.length === 0) {
    pane.innerHTML = `
      <div class="empty-state">
        No tasks yet.<br>
        <button class="btn-primary" style="margin-top:12px" onclick="refineAndGenerate('${planId}')">⚡ Generate tasks</button>
      </div>`;
    return;
  }

  // Reset UI selected task if it belongs to a different plan
  if (state.uiSelectedTaskId && !allTasks.find(t => t.id === state.uiSelectedTaskId)) {
    state.uiSelectedTaskId = null;
  }

  // Reset obsolete filter values
  if (state.taskFilter === 'SELECTED') state.taskFilter = 'all';
  const filtered = state.taskFilter === 'all'
    ? allTasks
    : allTasks.filter(t => (t.status || 'TODO') === state.taskFilter);

  const uiSel = state.uiSelectedTaskId;
  const uiTask = uiSel ? allTasks.find(t => t.id === uiSel) : null;
  const uiDone = uiTask && uiTask.status === 'DONE';
  const hasBulkSelection = state.bulkSelectedTaskIds.length > 0;

  const taskRows = filtered.map(t => {
    const status = t.status || 'TODO';
    const icon = TASK_ICONS[status] || '·';
    const isUiSelected = t.id === uiSel;
    const isBulkSelected = state.bulkSelectedTaskIds.includes(t.id);
    const bulkIndex = state.bulkSelectedTaskIds.indexOf(t.id) + 1; // 1-based
    const rowClass = `task-item${isUiSelected ? ' ui-selected' : ''}${isBulkSelected ? ' bulk-selected' : ''}`;
    const titleClass = status === 'DONE' ? 'done' : status === 'IN_PROGRESS' ? 'active' : '';
    const taskType = t.type || 'dev';
    const bulkNumber = isBulkSelected ? `<span class="bulk-number">${bulkIndex}</span>` : '';
    const inlineType = `
      <select class="task-inline-type" data-task-id="${t.id}" data-plan-id="${planId}">
        <option value="dev"   ${taskType === 'dev'   ? 'selected' : ''}>⌨ dev</option>
        <option value="debug" ${taskType === 'debug' ? 'selected' : ''}>⚙ debug</option>
        <option value="doc"   ${taskType === 'doc'   ? 'selected' : ''}>✎ doc</option>
      </select>`;
    const inlineStatus = `
      <select class="task-inline-status task-inline-status-${status.toLowerCase()}" data-task-id="${t.id}" data-plan-id="${planId}" data-title="${escHtml(t.title || '')}">
        <option value="TODO" ${status === 'TODO' ? 'selected' : ''}>· Todo</option>
        <option value="IN_PROGRESS" ${status === 'IN_PROGRESS' ? 'selected' : ''}>▶ In Progress</option>
        <option value="DONE" ${status === 'DONE' ? 'selected' : ''}>✓ Done</option>
        <option value="BLOCKED" ${status === 'BLOCKED' ? 'selected' : ''}>✗ Blocked</option>
      </select>`;

    const taskFiles = t.files || [];
    const fileWarnings = t.file_warnings || [];
    const hasWarnings = fileWarnings.length > 0;
    const filesHtml = taskFiles.length > 0 ? `<div class="task-files">${taskFiles.map(f => {
      const isImg = /\.(png|jpg|jpeg|gif|webp|bmp|svg)$/i.test(f);
      return `<span class="task-file-tag">${isImg ? '🖼' : '📄'} ${escHtml(f)}</span>`;
    }).join('')}</div>` : '';
    const warnTitle = hasWarnings ? fileWarnings.map(w => `${w.file}: ${w.reason}`).join('\n') : '';
    const warnBadge = hasWarnings ? `<span class="file-warn-badge" title="${escHtml(warnTitle)}">⚠</span>` : '';

    return `
      <div class="${rowClass}" data-task-id="${t.id}" data-plan-id="${planId}">
        <div class="task-icon ${status.toLowerCase()}">${icon}</div>
        <div class="task-body">
          <div class="task-title ${titleClass}">${escHtml(t.title || '')}${warnBadge}</div>
          ${t.description ? `<div class="task-desc">${escHtml(t.description)}</div>` : ''}
          ${t.blocked_reason ? `<div class="task-desc blocked-reason">↳ ${escHtml(t.blocked_reason)}</div>` : ''}
          ${filesHtml}
        </div>
        ${inlineType}
        ${inlineStatus}
        ${status !== 'DONE' ? `<div class="task-checkbox-wrapper">
          ${bulkNumber}
          <input type="checkbox" class="task-checkbox" data-task-id="${t.id}" ${isBulkSelected ? 'checked' : ''}>
        </div>` : ''}
        <button class="task-delete-btn btn-danger-ghost" title="Delete task" onclick="event.stopPropagation();uiDeleteTask('${planId}','${t.id}','${escHtml(t.title||'')}')">✕</button>
      </div>`;
  }).join('');

  // Filter buttons
  const filters = [
    ['all', 'All', stats.total || 0],
    ['TODO', 'Todo', stats.TODO || 0],
    ['IN_PROGRESS', 'In progress', stats.IN_PROGRESS || 0],
    ['DONE', 'Done', stats.DONE || 0],
  ];
  const filterBar = filters.map(([val, label, count]) =>
    `<button class="filter-btn ${state.taskFilter === val ? 'active' : ''}" data-filter="${val}">${label} <span class="filter-count">${count}</span></button>`
  ).join('');

  // Action toolbar - active based on UI selected task
  const isActive = plan.status === 'ACTIVE';
  const noSel = !uiSel;
  const dis = (noSel || !isActive) ? ' disabled' : '';
  const bulkCount = state.bulkSelectedTaskIds.length;
  const disLlm = (!isActive) ? ' disabled' : (bulkCount > 0 ? '' : dis);

  // Select all / deselect all button
  const selectAllBtn = hasBulkSelection
    ? `<button class="task-action-btn btn-deselect-all" onclick="clearBulkSelection()">✕ Deselect All</button>`
    : `<button class="task-action-btn btn-select-all" onclick="selectAllTasks('${planId}')">☑ Select All</button>`;

  // Run/Stop button logic
  const runLabel = bulkCount > 0 ? `⇒ Run ${bulkCount}` : '▶ Run';
  const runTitle = bulkCount > 0
    ? `Execute ${bulkCount} selected task${bulkCount > 1 ? 's' : ''} in sequence`
    : isActive ? 'Run selected task' : 'Only available on active track';
  
  const runStopButton = state.outputRunning
    ? `<button class="task-action-btn btn-stop" title="Stop current run" onclick="uiStopRun()" style="background-color: #ff6b6b; color: white;">⏹ Stop</button>`
    : `<button class="task-action-btn btn-run" title="${runTitle}"${disLlm} onclick="uiRunTask()">${runLabel}</button>`;

  const _savedAutoDone = $id('action-auto-done')?.checked ?? true;
  const _savedScroll = pane.querySelector('.tasks-scroll')?.scrollTop || 0;
  const headerActions = $id('plan-header-actions');
  if (headerActions) headerActions.innerHTML = '';
  pane.innerHTML = `
    <div class="tasks-toolbar-wrap">
      <div class="tasks-toolbar">
        <div class="filter-bar">${filterBar}</div>
        <div class="tasks-actions-row">
          <button class="task-action-btn btn-add" title="Add task" onclick="openAddTaskModal('${planId}')">+ Add task</button>
          <button class="task-action-btn btn-edit" title="Edit"${dis} onclick="uiEditTask()">✎ Edit</button>
          ${runStopButton}
          <button class="task-action-btn btn-review" title="${isActive ? 'Review' : 'Only available on active track'}"${disLlm} onclick="uiReviewTask()">⊙ Review</button>
          <label class="auto-done-label" title="Mark task as done when run completes">
            <input type="checkbox" id="action-auto-done" checked>
            Auto-done
          </label>
          ${selectAllBtn}
        </div>
      </div>
    </div>
    <div class="tasks-scroll">
      <div class="tasks-list">${taskRows || '<div class="empty-state" style="padding:20px 0">No tasks match this filter.</div>'}</div>
    </div>`;
  if (_savedScroll) pane.querySelector('.tasks-scroll').scrollTop = _savedScroll;
  const autoDoneEl = $id('action-auto-done');
  if (autoDoneEl) autoDoneEl.checked = _savedAutoDone;

  // Filter buttons
  pane.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.taskFilter = btn.dataset.filter;
      renderTasks(plan);
    });
  });

  // Clickable rows (toggle UI selection when clicking on row body, not checkbox)
  pane.querySelectorAll('.task-item').forEach(row => {
    row.addEventListener('click', (e) => {
      // If clicked directly on checkbox, let the checkbox handler deal with it
      if (e.target.classList.contains('task-checkbox')) return;

      const tid = row.dataset.taskId;
      state.uiSelectedTaskId = state.uiSelectedTaskId === tid ? null : tid;
      renderTasks(plan);
    });
  });

  // Checkbox handlers for bulk selection
  pane.querySelectorAll('.task-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', (e) => {
      const taskId = e.target.dataset.taskId;
      if (e.target.checked) {
        if (!state.bulkSelectedTaskIds.includes(taskId)) {
          state.bulkSelectedTaskIds.push(taskId);
        }
      } else {
        state.bulkSelectedTaskIds = state.bulkSelectedTaskIds.filter(id => id !== taskId);
      }
      renderTasks(plan);
    });
  });

  // Inline status selects - prevent row click propagation, handle status change
  pane.querySelectorAll('.task-inline-status').forEach(sel => {
    sel.addEventListener('click', e => e.stopPropagation());
    sel.addEventListener('change', async e => {
      e.stopPropagation();
      const { taskId, planId: pid, title } = sel.dataset;
      await handleTaskStatusChange(pid, taskId, e.target.value, title);
    });
  });

  // Inline type selects - save task type directly
  pane.querySelectorAll('.task-inline-type').forEach(sel => {
    sel.addEventListener('click', e => e.stopPropagation());
    sel.addEventListener('change', async e => {
      e.stopPropagation();
      const { taskId, planId: pid } = sel.dataset;
      await api.updateTask(pid, taskId, { type: e.target.value });
    });
  });
}

// -- Bulk selection helpers --------------------------------------------------
function selectAllTasks(planId) {
  const plan = state._lastPlan;
  if (!plan) return;
  // Exclude tasks from LOCKED or DONE phases
  const excludedPhaseIds = new Set(
    (plan.phases || []).filter(p => p.status === 'LOCKED' || p.status === 'DONE').map(p => p.id)
  );
  const allTasks = plan.tasks || [];
  state.bulkSelectedTaskIds = allTasks
    .filter(t => (t.status || 'TODO') === 'TODO' && !excludedPhaseIds.has(t.phase_id))
    .map(t => t.id);
  renderTasks(plan);
}

function clearBulkSelection() {
  state.bulkSelectedTaskIds = [];
  const plan = state._lastPlan;
  if (plan) renderTasks(plan);
}

// -- Phase-grouped tasks rendering --------------------------------------------
function renderTasksWithPhases(plan, phases) {
  const planId = plan.id;
  const pane = $id('tab-tasks');
  const uiSel = state.uiSelectedTaskId;

  // Global action bar (uses selected task regardless of phase)
  const isActive = plan.status === 'ACTIVE';
  const uiTask = uiSel ? (plan.tasks || []).find(t => t.id === uiSel) : null;
  const noSel = !uiSel;
  const uiDone = uiTask && uiTask.status === 'DONE';
  const dis = (noSel || !isActive) ? ' disabled' : '';
  const hasBulkSelection = state.bulkSelectedTaskIds.length > 0;
  const bulkCount = state.bulkSelectedTaskIds.length;
  const disLlm = (!isActive) ? ' disabled' : (bulkCount > 0 ? '' : dis);

  // Select all / deselect all button
  const selectAllBtn = hasBulkSelection
    ? `<button class="task-action-btn btn-deselect-all" onclick="clearBulkSelection()">✕ Deselect All</button>`
    : `<button class="task-action-btn btn-select-all" onclick="selectAllTasks('${planId}')">☑ Select All</button>`;

  // Run/Stop button logic
  const runLabel = bulkCount > 0 ? `⇒ Run ${bulkCount}` : '▶ Run';
  const runTitle = bulkCount > 0
    ? `Execute ${bulkCount} selected task${bulkCount > 1 ? 's' : ''} in sequence`
    : isActive ? 'Run selected task' : 'Only available on active track';
  
  const runStopBtn = state.outputRunning
    ? `<button class="task-action-btn btn-stop" title="Stop current run" onclick="uiStopRun()" style="background-color: #ff6b6b; color: white;">⏹ Stop</button>`
    : `<button class="task-action-btn btn-run" title="${runTitle}"${disLlm} onclick="uiRunTask()">${runLabel}</button>`;

  const actionsRow = `
    <button class="task-action-btn btn-add" title="Add phase" onclick="openNewPhaseModal('${planId}')">+ Add Phase</button>
    <button class="task-action-btn btn-add" title="Add task" onclick="openAddTaskModal('${planId}')">+ Add task</button>
    <button class="task-action-btn btn-edit" title="Edit"${dis} onclick="uiEditTask()">✎ Edit</button>
    ${runStopBtn}
    <button class="task-action-btn btn-review" title="${isActive ? 'Review' : 'Only available on active track'}"${disLlm} onclick="uiReviewTask()">⊙ Review</button>
    <label class="auto-done-label" title="Mark task as done when run completes">
      <input type="checkbox" id="action-auto-done" checked>
      Auto-done
    </label>
    ${selectAllBtn}`;

  // Compute global stats across all phases for the filter bar
  const allTasks = phases.flatMap(ph => ph.tasks || []);
  const globalStats = { total: allTasks.length, TODO: 0, IN_PROGRESS: 0, DONE: 0 };
  allTasks.forEach(t => { const s = t.status || 'TODO'; if (s in globalStats) globalStats[s]++; });

  const phaseFilters = [
    ['all', 'All', globalStats.total],
    ['TODO', 'Todo', globalStats.TODO],
    ['IN_PROGRESS', 'In progress', globalStats.IN_PROGRESS],
    ['DONE', 'Done', globalStats.DONE],
  ];
  const filterBar = phaseFilters.map(([val, label, count]) =>
    `<button class="filter-btn ${state.taskFilter === val ? 'active' : ''}" data-filter="${val}">${label} <span class="filter-count">${count}</span></button>`
  ).join('');

  const phaseSections = phases.map(ph => {
    const phStatus = ph.status || 'TODO';
    const isLocked = phStatus === 'LOCKED';
    const phStats = ph.stats || {};
    const phDone = phStats.DONE || 0;
    const phTotal = phStats.total || 0;
    const pct = phTotal > 0 ? Math.round(phDone / phTotal * 100) : 0;
    const phaseTasks = ph.tasks || [];

    const lockIcon = isLocked ? '🔒' : (phStatus === 'DONE' ? '✓' : '🔓');
    const depNames = (ph.depends_on || []).map(depId => {
      const dep = phases.find(p => p.id === depId);
      return dep ? dep.name : depId;
    }).join(', ');

    const filteredTasks = state.taskFilter === 'all'
      ? phaseTasks
      : phaseTasks.filter(t => (t.status || 'TODO') === state.taskFilter);

    const taskRows = filteredTasks.map(t => {
      const status = t.status || 'TODO';
      const icon = TASK_ICONS[status] || '·';
      const isUiSelected = t.id === uiSel;
      const isBulkSelected = state.bulkSelectedTaskIds.includes(t.id);
      const bulkIndex = state.bulkSelectedTaskIds.indexOf(t.id) + 1; // 1-based
      const titleClass = status === 'DONE' ? 'done' : status === 'IN_PROGRESS' ? 'active' : '';
      const taskType = t.type || 'dev';
      const bulkNumber = isBulkSelected ? `<span class="bulk-number">${bulkIndex}</span>` : '';
      const inlineType = `
        <select class="task-inline-type" data-task-id="${t.id}" data-plan-id="${planId}" ${isLocked ? 'disabled' : ''}>
          <option value="dev"   ${taskType === 'dev'   ? 'selected' : ''}>⌨ dev</option>
          <option value="debug" ${taskType === 'debug' ? 'selected' : ''}>⚙ debug</option>
          <option value="doc"   ${taskType === 'doc'   ? 'selected' : ''}>✎ doc</option>
        </select>`;
      const inlineStatus = `
        <select class="task-inline-status task-inline-status-${status.toLowerCase()}" data-task-id="${t.id}" data-plan-id="${planId}" data-title="${escHtml(t.title || '')}" ${isLocked ? 'disabled' : ''}>
          <option value="TODO" ${status === 'TODO' ? 'selected' : ''}>· Todo</option>
          <option value="IN_PROGRESS" ${status === 'IN_PROGRESS' ? 'selected' : ''}>▶ In Progress</option>
          <option value="DONE" ${status === 'DONE' ? 'selected' : ''}>✓ Done</option>
          <option value="BLOCKED" ${status === 'BLOCKED' ? 'selected' : ''}>✗ Blocked</option>
        </select>`;
      const tFiles = t.files || [];
      const tWarnings = t.file_warnings || [];
      const tHasWarnings = tWarnings.length > 0;
      const tFilesHtml = tFiles.length > 0 ? `<div class="task-files">${tFiles.map(f => {
        const isImg = /\.(png|jpg|jpeg|gif|webp|bmp|svg)$/i.test(f);
        return `<span class="task-file-tag">${isImg ? '🖼' : '📄'} ${escHtml(f)}</span>`;
      }).join('')}</div>` : '';
      const tWarnTitle = tHasWarnings ? tWarnings.map(w => `${w.file}: ${w.reason}`).join('\n') : '';
      const tWarnBadge = tHasWarnings ? `<span class="file-warn-badge" title="${escHtml(tWarnTitle)}">⚠</span>` : '';
      return `
        <div class="task-item${isUiSelected ? ' ui-selected' : ''}${isBulkSelected ? ' bulk-selected' : ''}${isLocked ? ' task-locked' : ''}" data-task-id="${t.id}" data-plan-id="${planId}">
          <div class="task-icon ${status.toLowerCase()}">${icon}</div>
          <div class="task-body">
            <div class="task-title ${titleClass}">${escHtml(t.title || '')}${tWarnBadge}</div>
            ${t.description ? `<div class="task-desc">${escHtml(t.description)}</div>` : ''}
            ${tFilesHtml}
          </div>
          ${inlineType}
          ${inlineStatus}
          ${status !== 'DONE' ? `<div class="task-checkbox-wrapper">
            ${bulkNumber}
            <input type="checkbox" class="task-checkbox" data-task-id="${t.id}" ${isBulkSelected ? 'checked' : ''} ${isLocked ? 'disabled' : ''}>
          </div>` : ''}
          <button class="task-delete-btn btn-danger-ghost" title="Delete task" onclick="event.stopPropagation();uiDeleteTask('${planId}','${t.id}','${escHtml(t.title||'')}')">✕</button>
        </div>`;
    }).join('');

    const emptyState = phaseTasks.length === 0
      ? `<div class="phase-empty">No tasks yet. <button class="btn-ghost btn-sm" onclick="generateTasksForPhase('${planId}','${ph.id}')">⚡ Generate</button></div>`
      : filteredTasks.length === 0
        ? `<div class="phase-empty" style="color:var(--text-dim)">No ${state.taskFilter} tasks.</div>`
        : '';

    // Per-phase checkbox: select/deselect all TODO tasks in this phase
    const phaseTodoTasks = phaseTasks.filter(t => (t.status || 'TODO') === 'TODO');
    const phaseSelectedCount = phaseTodoTasks.filter(t => state.bulkSelectedTaskIds.includes(t.id)).length;
    const phaseAllSelected = phaseTodoTasks.length > 0 && phaseSelectedCount === phaseTodoTasks.length;
    const phaseCheckbox = !isLocked && phaseTodoTasks.length > 0
      ? `<input type="checkbox" class="phase-select-checkbox" data-phase-id="${ph.id}"
             title="Select all TODO tasks in this phase" ${phaseAllSelected ? 'checked' : ''}>`
      : '';

    const isCollapsed = state.collapsedPhases.has(ph.id);
    const chevron = `<span class="phase-chevron">${isCollapsed ? '▸' : '▾'}</span>`;

    return `
      <div class="phase-section ${isLocked ? 'phase-locked' : ''}${isCollapsed ? ' phase-collapsed' : ''}" data-phase-id="${ph.id}">
        <div class="phase-header" onclick="togglePhase('${ph.id}')">
          ${chevron}
          <span class="phase-lock-icon">${lockIcon}</span>
          <span class="phase-name">${escHtml(ph.name)}</span>
          <span class="phase-badge phase-badge-${phStatus.toLowerCase()}">${phStatus}</span>
          ${isLocked && depNames ? `<span class="phase-dep-info">← needs: ${escHtml(depNames)}</span>` : ''}
          <span class="phase-progress-wrap">
            <span class="phase-task-count">${phDone}/${phTotal}</span>
            <div class="phase-progress-bar"><div class="phase-progress-fill" style="width:${pct}%"></div></div>
          </span>
          <span class="phase-actions" onclick="event.stopPropagation()">
            ${!isLocked && phaseTasks.length === 0 ? `<button class="btn-ghost btn-sm" onclick="generateTasksForPhase('${planId}','${ph.id}')">⚡ Tasks</button>` : ''}
            <button class="btn-ghost btn-sm btn-danger-ghost" title="Delete phase and all its tasks" onclick="uiDeletePhase('${planId}','${ph.id}','${escHtml(ph.name)}')">✕</button>
            ${phaseCheckbox}
          </span>
        </div>
        ${ph.description ? `<div class="phase-description">${escHtml(ph.description)}</div>` : ''}
        <div class="phase-tasks${isLocked ? ' phase-tasks-locked' : ''}">
          ${taskRows || emptyState}
        </div>
      </div>`;
  }).join('');

  const _savedAutoDone = $id('action-auto-done')?.checked ?? true;
  const _savedScroll = pane.querySelector('.tasks-scroll')?.scrollTop || 0;
  const headerActions = $id('plan-header-actions');
  if (headerActions) headerActions.innerHTML = '';
  pane.innerHTML = `
    <div class="tasks-toolbar-wrap">
      <div class="tasks-toolbar">
        <div class="filter-bar">${filterBar}</div>
        <div class="tasks-actions-row">${actionsRow}</div>
      </div>
    </div>
    <div class="tasks-scroll"><div class="phase-list">${phaseSections}</div></div>`;
  if (_savedScroll) pane.querySelector('.tasks-scroll').scrollTop = _savedScroll;
  const autoDoneEl = $id('action-auto-done');
  if (autoDoneEl) autoDoneEl.checked = _savedAutoDone;

  // Filter button binding
  pane.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.taskFilter = btn.dataset.filter;
      renderTasksWithPhases(plan, phases);
    });
  });

  // Bind task clicks (toggle UI selection when clicking on row body, not checkbox)
  pane.querySelectorAll('.task-item:not(.task-locked)').forEach(row => {
    row.addEventListener('click', (e) => {
      // If clicked directly on checkbox, let the checkbox handler deal with it
      if (e.target.classList.contains('task-checkbox')) return;

      const tid = row.dataset.taskId;
      state.uiSelectedTaskId = state.uiSelectedTaskId === tid ? null : tid;
      renderTasksWithPhases(plan, phases);
    });
  });

  // Checkbox handlers for bulk selection
  pane.querySelectorAll('.task-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', (e) => {
      const taskId = e.target.dataset.taskId;
      if (e.target.checked) {
        if (!state.bulkSelectedTaskIds.includes(taskId)) {
          state.bulkSelectedTaskIds.push(taskId);
        }
      } else {
        state.bulkSelectedTaskIds = state.bulkSelectedTaskIds.filter(id => id !== taskId);
      }
      renderTasksWithPhases(plan, phases);
    });
  });

  // Inline status selects - prevent row click propagation, handle status change
  pane.querySelectorAll('.task-inline-status').forEach(sel => {
    sel.addEventListener('click', e => e.stopPropagation());
    sel.addEventListener('change', async e => {
      e.stopPropagation();
      const { taskId, planId: pid, title } = sel.dataset;
      await handleTaskStatusChange(pid, taskId, e.target.value, title);
    });
  });

  // Inline type selects - save task type directly
  pane.querySelectorAll('.task-inline-type').forEach(sel => {
    sel.addEventListener('click', e => e.stopPropagation());
    sel.addEventListener('change', async e => {
      e.stopPropagation();
      const { taskId, planId: pid } = sel.dataset;
      await api.updateTask(pid, taskId, { type: e.target.value });
    });
  });

  // Per-phase select checkboxes
  pane.querySelectorAll('.phase-select-checkbox').forEach(checkbox => {
    const phaseId = checkbox.dataset.phaseId;
    const phase = phases.find(p => p.id === phaseId);
    if (!phase) return;
    const phaseTodoIds = (phase.tasks || [])
      .filter(t => (t.status || 'TODO') === 'TODO')
      .map(t => t.id);
    // Set indeterminate if some (but not all) are selected
    const selectedCount = phaseTodoIds.filter(id => state.bulkSelectedTaskIds.includes(id)).length;
    if (selectedCount > 0 && selectedCount < phaseTodoIds.length) checkbox.indeterminate = true;

    checkbox.addEventListener('click', e => e.stopPropagation());
    checkbox.addEventListener('change', e => {
      e.stopPropagation();
      if (e.target.checked) {
        phaseTodoIds.forEach(id => {
          if (!state.bulkSelectedTaskIds.includes(id)) state.bulkSelectedTaskIds.push(id);
        });
      } else {
        state.bulkSelectedTaskIds = state.bulkSelectedTaskIds.filter(id => !phaseTodoIds.includes(id));
      }
      renderTasksWithPhases(plan, phases);
    });
  });
}

// -- Phase generation ---------------------------------------------------------
function generatePhases(planId) {
  state.outputText = '';
  state.outputRunning = true;
  _openOutputTerminal(planId, '⚡ Gen phases');
  _setOutputHeader('▶ Generating phases…');

  _startStream(`/api/tracks/${planId}/phases/generate`, {
    onMeta: (t) => { _setOutputHeader('▶ ' + t); },
    onText: _appendOutput,
    onDone: () => { state.outputRunning = false; refresh(); },
    onError: () => { state.outputRunning = false; _appendOutput('\n⚠ Connection error\n'); },
  });
}

function generateTasksForPhase(planId, phaseId) {
  state.outputText = '';
  state.outputRunning = true;
  _openOutputTerminal(planId, '⚡ Gen tasks');
  _setOutputHeader('▶ Generating tasks for phase…');

  _startStream(`/api/tracks/${planId}/phases/${phaseId}/tasks/generate`, {
    onMeta: (t) => { _setOutputHeader('▶ ' + t); },
    onText: _appendOutput,
    onDone: () => { state.outputRunning = false; renderPanelFor(planId); },
    onError: () => { state.outputRunning = false; _appendOutput('\n⚠ Connection error\n'); },
  });
}

function runArcheScan() {
  state.outputText = '';
  state.outputRunning = true;
  _openOutputTerminal('scan', '⚡ Scan Architecture');
  _setOutputHeader('▶ Scanning project architecture…');

  _startStream(`/api/scan`, {
    onMeta: (t) => { _setOutputHeader('▶ ' + t); },
    onText: _appendOutput,
    onDone: () => {
      state.outputRunning = false;
      _appendOutput('\n✓ Architecture scan complete\n');
      // Refresh the architecture view
      if (state.selectedPlanId) renderPanelFor(state.selectedPlanId);
      // Refresh archi content
      showArchiModal();
    },
    onError: () => { state.outputRunning = false; _appendOutput('\n⚠ Connection error\n'); },
  });
}

async function uiDeleteTask(planId, taskId, taskTitle) {
  if (!confirm(`Delete task "${taskTitle}"?`)) return;
  await apiFetch(`/api/tracks/${planId}/tasks/${taskId}`, { method: 'DELETE' });
  await renderPanelFor(planId);
}

async function uiDeletePhase(planId, phaseId, phaseName) {
  if (!confirm(`Delete phase "${phaseName}" and all its tasks?`)) return;
  await api.deletePhase(planId, phaseId);
  await renderPanelFor(planId);
}

// -- Phase collapse toggle -----------------------------------------------------
function togglePhase(phaseId) {
  if (state.collapsedPhases.has(phaseId)) {
    state.collapsedPhases.delete(phaseId);
  } else {
    state.collapsedPhases.add(phaseId);
  }
  if (state.selectedPlanId) renderPanelFor(state.selectedPlanId);
}

// -- New phase modal ----------------------------------------------------------
function openNewPhaseModal(planId) {
  state.newPhasePlanId = planId;
  $id('modal-phase-name').value = '';
  $id('modal-phase-desc').value = '';
  $id('modal-phase-overlay').classList.remove('hidden');
  setTimeout(() => $id('modal-phase-name').focus(), 50);
}

function closePhaseModal() {
  $id('modal-phase-overlay').classList.add('hidden');
  state.newPhasePlanId = null;
}

async function openArchiModal() {
  const data = await api.getArchi();
  $id('archi-content').textContent = data?.content?.trim() || '(empty - run arche scan to generate)';
  $id('archi-hint').textContent = data?.exists ? 'storage/archi.md' : 'not generated yet';
  $id('modal-archi-overlay').classList.remove('hidden');
}

function closeArchiModal() {
  $id('modal-archi-overlay').classList.add('hidden');
}

async function openMemoryModal() {
  const data = await api.getMemory();
  $id('memory-content').textContent = data?.content?.trim() || '(empty - no cross-track discoveries yet)';
  $id('modal-memory-overlay').classList.remove('hidden');
}

function closeMemoryModal() {
  $id('modal-memory-overlay').classList.add('hidden');
}

async function clearMemory() {
  if (!confirm('Clear all shared memory? This cannot be undone.')) return;
  await api.clearMemory();
  $id('memory-content').textContent = '(empty)';
}

async function confirmNewPhase() {
  const name = $id('modal-phase-name').value.trim();
  if (!name || !state.newPhasePlanId) return;
  const desc = $id('modal-phase-desc').value.trim();
  const planId = state.newPhasePlanId;
  closePhaseModal();
  await api.createPhase(planId, name, desc);
  await renderPanelFor(planId);
}

// -- Agents panel --------------------------------------------------------------
function toggleAgentsView(show) {
  const panel = $id('panel');
  const agentsPanel = $id('agents-panel');
  const btn = $id('sidebar-agents-btn');
  if (show) {
    panel.style.display = 'none';
    $id('instructions-panel').classList.remove('visible');
    $id('sidebar-instructions-btn').classList.remove('active');
    agentsPanel.classList.add('visible');
    btn.classList.add('active');
  } else {
    panel.style.display = '';
    agentsPanel.classList.remove('visible');
    btn.classList.remove('active');
  }
}

function _buildAgentItem(agent) {
  const item = document.createElement('div');
  item.className = 'agent-item';
  if (agent) item.dataset.id = agent.id;
  const modelBadge = agent && agent.model
    ? `<span class="agent-model">${escHtml(agent.model)}</span>`
    : '';
  item.innerHTML = `
    <div class="agent-header">
      <span class="agent-name">${escHtml(agent ? agent.name : 'New agent')}</span>
      <span class="agent-role">${escHtml(agent ? (agent.role || '') : '')}</span>
      ${modelBadge}
    </div>
    <div class="agent-description">${escHtml(agent ? (agent.description || '') : '')}</div>
    <div class="agent-edit-content" style="display:none;">
      <div class="agent-edit-row">
        <div class="agent-edit-field">
          <label>Name</label>
          <input type="text" class="agent-edit-name" value="${escHtml(agent ? agent.name : '')}" placeholder="Agent name">
        </div>
        <div class="agent-edit-field">
          <label>Role</label>
          <input type="text" class="agent-edit-role" value="${escHtml(agent ? (agent.role || '') : '')}" placeholder="developer, qa...">
        </div>
        <div class="agent-edit-field">
          <label>Model</label>
          <input type="text" class="agent-edit-model" value="${escHtml(agent ? (agent.model || '') : '')}" placeholder="optional">
        </div>
      </div>
      <div class="agent-edit-field agent-edit-desc-wrap">
        <label>Description</label>
        <input type="text" class="agent-edit-desc" value="${escHtml(agent ? (agent.description || '') : '')}" placeholder="Short description">
      </div>
      <textarea class="instruction-editor agent-edit-prompt" placeholder="System prompt...">${escHtml(agent ? (agent.system_prompt || '') : '')}</textarea>
      <div class="instruction-editor-actions">
        <button class="btn-agent-delete btn-ghost btn-sm" style="color:var(--red);margin-right:auto">Delete</button>
        <button class="btn-agent-save btn-save-instruction">Save</button>
        <button class="btn-agent-discard btn-cancel-edit">Discard</button>
      </div>
    </div>
  `;
  return item;
}

function _attachAgentItemListeners(item, isNew) {
  const agentId = item.dataset.id;
  const nameEl = item.querySelector('.agent-name');
  const editContent = item.querySelector('.agent-edit-content');

  nameEl.addEventListener('click', () => {
    const isOpen = editContent.style.display !== 'none';
    editContent.style.display = isOpen ? 'none' : 'block';
    nameEl.classList.toggle('editing', !isOpen);
    if (!isOpen) item.querySelector('.agent-edit-name').focus();
  });

  item.querySelector('.btn-agent-discard').addEventListener('click', () => {
    if (isNew) { item.remove(); return; }
    editContent.style.display = 'none';
    nameEl.classList.remove('editing');
  });

  item.querySelector('.btn-agent-save').addEventListener('click', async () => {
    const data = {
      name: item.querySelector('.agent-edit-name').value.trim(),
      role: item.querySelector('.agent-edit-role').value.trim(),
      model: item.querySelector('.agent-edit-model').value.trim() || null,
      description: item.querySelector('.agent-edit-desc').value.trim(),
      system_prompt: item.querySelector('.agent-edit-prompt').value.trim(),
    };
    if (!data.name) { alert('Name is required'); return; }
    try {
      if (isNew) {
        await api.createAgent(data);
      } else {
        await api.updateAgent(agentId, data);
      }
      await loadAgents($id('agent-search')?.value || '');
    } catch (err) {
      alert('Failed to save agent: ' + err.message);
    }
  });

  item.querySelector('.btn-agent-delete').addEventListener('click', async () => {
    if (isNew) { item.remove(); return; }
    if (!confirm('Delete this agent?')) return;
    try {
      await api.deleteAgent(agentId);
      await loadAgents($id('agent-search')?.value || '');
    } catch (err) {
      alert('Failed to delete agent: ' + err.message);
    }
  });
}

async function loadAgents(searchQuery = '') {
  const listContainer = $id('agent-list');
  if (!listContainer) return;
  listContainer.innerHTML = '';

  try {
    const response = await api.listAgents();
    if (!response) throw new Error('Failed to fetch agents');
    let agents = response.agents || [];

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      agents = agents.filter(a =>
        a.name.toLowerCase().includes(q) ||
        (a.description || '').toLowerCase().includes(q) ||
        (a.role || '').toLowerCase().includes(q)
      );
    }

    if (agents.length === 0) {
      listContainer.innerHTML = `
        <div class="agents-empty-state">
          <div class="empty-state-icon">🤖</div>
          <p class="empty-state-text">No agents found</p>
          <p class="empty-state-subtext">Create an agent to get started</p>
        </div>
      `;
      return;
    }

    agents.forEach(agent => {
      const item = _buildAgentItem(agent);
      listContainer.appendChild(item);
      _attachAgentItemListeners(item, false);
    });

  } catch (err) {
    console.error('Error loading agents:', err);
    listContainer.innerHTML = '<div class="error">Failed to load agents</div>';
  }
}

async function renderAgents() {
  const pane = $id('agents-panel');
  pane.innerHTML = `
    <div class="agents-layout">
      <div class="agents-toolbar">
        <input type="text" id="agent-search" placeholder="Search agents..." />
        <button class="btn-new-agent" id="btn-new-agent">+ New Agent</button>
      </div>
      <div id="agent-list"></div>
    </div>
  `;

  await loadAgents();

  $id('agent-search').addEventListener('input', debounce(async (e) => {
    await loadAgents(e.target.value);
  }, 300));

  $id('btn-new-agent').addEventListener('click', () => {
    const listContainer = $id('agent-list');
    const emptyState = listContainer.querySelector('.agents-empty-state');
    if (emptyState) emptyState.remove();
    const item = _buildAgentItem(null);
    listContainer.insertBefore(item, listContainer.firstChild);
    _attachAgentItemListeners(item, true);
    item.querySelector('.agent-edit-content').style.display = 'block';
    item.querySelector('.agent-name').classList.add('editing');
    item.querySelector('.agent-edit-name').focus();
  });
}

// -- Instructions panel --------------------------------------------------------
function toggleInstructionsView(show) {
  const panel = $id('panel');
  const instrPanel = $id('instructions-panel');
  const btn = $id('sidebar-instructions-btn');
  if (show) {
    panel.style.display = 'none';
    $id('agents-panel').classList.remove('visible');
    $id('sidebar-agents-btn').classList.remove('active');
    instrPanel.classList.add('visible');
    btn.classList.add('active');
  } else {
    panel.style.display = '';
    instrPanel.classList.remove('visible');
    btn.classList.remove('active');
  }
}

async function renderInstructions() {
  const pane = $id('instructions-panel');
  pane.innerHTML = `
    <div class="instructions-layout">
      <div class="instructions-search">
        <input type="text" id="instruction-search" placeholder="Search instructions..." />
        <div class="instructions-filter-bar">
          <button class="instr-filter-btn active" data-filter="all">Tous</button>
          <button class="instr-filter-btn" data-filter="selected">Selected</button>
        </div>
        <button id="btn-new-instruction" class="btn-new-instruction">+ New</button>
      </div>
      <div id="new-instruction-form" class="new-instruction-form" style="display: none;">
        <div class="new-instruction-form-row">
          <input type="text" id="new-instr-name" placeholder="Name *" class="new-instr-field" />
          <input type="text" id="new-instr-category" placeholder="Category" class="new-instr-field" />
          <input type="text" id="new-instr-tags" placeholder="Tags (comma-separated)" class="new-instr-field" />
        </div>
        <input type="text" id="new-instr-description" placeholder="Description" class="new-instr-field new-instr-full" />
        <textarea id="new-instr-content" class="new-instr-content" placeholder="Instruction content *"></textarea>
        <div class="new-instruction-actions">
          <button id="btn-save-new-instruction" class="btn-save-instruction">Save</button>
          <button id="btn-cancel-new-instruction" class="btn-cancel-edit">Cancel</button>
        </div>
      </div>
      <div id="instruction-list"></div>
    </div>
  `;

  // Load and display instructions
  await loadInstructions();

  // Search
  $id('instruction-search').addEventListener('input', debounce(loadInstructions, 300));

  // Filter buttons
  pane.querySelectorAll('.instr-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      pane.querySelectorAll('.instr-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      loadInstructions();
    });
  });

  // New instruction form toggle
  $id('btn-new-instruction').addEventListener('click', () => {
    const form = $id('new-instruction-form');
    const visible = form.style.display !== 'none';
    form.style.display = visible ? 'none' : 'block';
    if (!visible) $id('new-instr-name').focus();
  });

  $id('btn-cancel-new-instruction').addEventListener('click', () => {
    $id('new-instruction-form').style.display = 'none';
    clearNewInstructionForm();
  });

  $id('btn-save-new-instruction').addEventListener('click', async () => {
    const name = $id('new-instr-name').value.trim();
    const content = $id('new-instr-content').value.trim();
    if (!name || !content) {
      alert('Name and content are required.');
      return;
    }
    const tagsRaw = $id('new-instr-tags').value.trim();
    const tags = tagsRaw ? tagsRaw.split(',').map(t => t.trim()).filter(Boolean) : [];
    const instruction = {
      id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''),
      name,
      description: $id('new-instr-description').value.trim(),
      category: $id('new-instr-category').value.trim() || 'user',
      tags,
      content,
      source: 'user',
      is_enabled: true,
    };
    try {
      const res = await api.addUserInstruction(instruction);
      if (!res || !res.success) throw new Error('Server returned failure');
      $id('new-instruction-form').style.display = 'none';
      clearNewInstructionForm();
      await loadInstructions();
    } catch (e) {
      console.error('Failed to save new instruction:', e);
      alert('Failed to save instruction: ' + e.message);
    }
  });
}

function clearNewInstructionForm() {
  $id('new-instr-name').value = '';
  $id('new-instr-description').value = '';
  $id('new-instr-tags').value = '';
  $id('new-instr-content').value = '';
  $id('new-instr-category').value = '';
}

async function loadInstructions() {
  const searchQuery = $id('instruction-search')?.value || '';
  const activeFilter = document.querySelector('.instr-filter-btn.active')?.dataset.filter || 'all';

  const listContainer = $id('instruction-list');
  listContainer.innerHTML = '';

  // Show loading skeleton
  for (let i = 0; i < 5; i++) {
    const skeleton = document.createElement('div');
    skeleton.className = 'instruction-skeleton';
    listContainer.appendChild(skeleton);
  }

  try {
    const params = {};
    if (searchQuery) params.q = searchQuery;

    const response = await api.searchInstructions(params);
    if (!response) {
      throw new Error('Failed to fetch instructions from server');
    }
    let instructions = response.instructions || [];

    // Client-side filter: selected only
    if (activeFilter === 'selected') {
      instructions = instructions.filter(i => state.selectedInstructionIds.has(i.id));
    }

    listContainer.innerHTML = '';

    if (instructions.length === 0) {
      listContainer.innerHTML = `
        <div class="instructions-empty-state">
          <div class="empty-state-icon">📚</div>
          <p class="empty-state-text">No instructions found</p>
          <p class="empty-state-subtext">Try adjusting your search or adding new instructions</p>
        </div>
      `;
      return;
    }
    
    instructions.forEach(instruction => {
      const item = document.createElement('div');
      item.className = 'instruction-item';
      const tagsHtml = instruction.tags && instruction.tags.length > 0 
        ? `<div class="instruction-tags">${instruction.tags.map(t => `<span class="tag">${escHtml(t)}</span>`).join(' ')}</div>`
        : '';
      const isEditable = instruction.source === 'user';
      item.dataset.source = instruction.source || '';
      item.dataset.category = instruction.category || '';
      item.innerHTML = `
        <div class="instruction-header">
          <input type="checkbox" class="instruction-checkbox" data-id="${instruction.id}" />
          <div class="instruction-name" data-id="${instruction.id}">${escHtml(instruction.name)}</div>
          <div class="instruction-category">${escHtml(instruction.category)}</div>
        </div>
        ${tagsHtml}
        <div class="instruction-description">${escHtml(instruction.description || '')}</div>
        <div class="instruction-content" style="display: none;">
          <pre class="instruction-viewer"></pre>
          <div class="instruction-viewer-actions">
            ${isEditable ? `<button class="btn-edit-instruction btn-secondary" data-id="${instruction.id}">Edit</button>` : ''}
            <button class="btn-cancel-edit" data-id="${instruction.id}">Close</button>
          </div>
          ${isEditable ? `
          <textarea class="instruction-editor" data-id="${instruction.id}" style="display:none;"></textarea>
          <div class="instruction-editor-actions" style="display:none;">
            <button class="btn-save-instruction" data-id="${instruction.id}">Save</button>
            <button class="btn-discard-edit" data-id="${instruction.id}">Discard</button>
          </div>` : ''}
        </div>
      `;
      listContainer.appendChild(item);
    });
    
    // Set up checkbox event listeners and restore checked state
    document.querySelectorAll('.instruction-checkbox').forEach(checkbox => {
      // Restore selection state after re-render
      if (state.selectedInstructionIds.has(checkbox.dataset.id)) {
        checkbox.checked = true;
      }
      checkbox.addEventListener('change', function() {
        const instructionId = this.dataset.id;
        if (this.checked) {
          state.selectedInstructionIds.add(instructionId);
        } else {
          state.selectedInstructionIds.delete(instructionId);
        }
        localStorage.setItem('selectedInstructionIds', JSON.stringify(Array.from(state.selectedInstructionIds)));
        updateInstructionSelectionFeedback();
      });
    });

    // Set up instruction name click to open viewer (read-only for all)
    document.querySelectorAll('.instruction-name').forEach(nameElement => {
      nameElement.addEventListener('click', async function() {
        const instructionId = this.dataset.id;
        const item = this.closest('.instruction-item');
        const contentElement = item.querySelector('.instruction-content');

        // Toggle visibility
        if (contentElement.style.display !== 'none') {
          contentElement.style.display = 'none';
          this.classList.remove('editing');
          return;
        }

        this.classList.add('editing');
        contentElement.style.display = 'block';

        // Load content into read-only viewer (lazy, only once)
        const viewer = contentElement.querySelector('.instruction-viewer');
        if (viewer && !viewer.dataset.loaded) {
          viewer.textContent = 'Loading…';
          try {
            let content = '';
            if (item.dataset.source === 'user') {
              const data = await api.getUserInstruction(instructionId);
              content = data.content || '';
            } else {
              const categoryParam = item.dataset.category ? `&category=${encodeURIComponent(item.dataset.category)}` : '';
              const data = await apiFetch(`/api/instructions/get?id=${encodeURIComponent(instructionId)}${categoryParam}`);
              content = data.content || '';
            }
            viewer.textContent = content;
            viewer.dataset.loaded = '1';
          } catch (e) {
            viewer.textContent = 'Failed to load content.';
            console.error('Failed to load instruction content', e);
          }
        }
      });
    });

    // Edit button: switch viewer → textarea
    document.querySelectorAll('.btn-edit-instruction').forEach(editBtn => {
      editBtn.addEventListener('click', function() {
        const item = this.closest('.instruction-item');
        const viewer = item.querySelector('.instruction-viewer');
        const textarea = item.querySelector('.instruction-editor');
        const viewerActions = item.querySelector('.instruction-viewer-actions');
        const editorActions = item.querySelector('.instruction-editor-actions');

        textarea.value = viewer.textContent;
        viewer.style.display = 'none';
        viewerActions.style.display = 'none';
        textarea.style.display = 'block';
        editorActions.style.display = 'flex';
        textarea.focus();
      });
    });

    // Discard button: switch textarea → viewer
    document.querySelectorAll('.btn-discard-edit').forEach(discardBtn => {
      discardBtn.addEventListener('click', function() {
        const item = this.closest('.instruction-item');
        const viewer = item.querySelector('.instruction-viewer');
        const textarea = item.querySelector('.instruction-editor');
        const viewerActions = item.querySelector('.instruction-viewer-actions');
        const editorActions = item.querySelector('.instruction-editor-actions');

        textarea.style.display = 'none';
        editorActions.style.display = 'none';
        viewer.style.display = 'block';
        viewerActions.style.display = 'flex';
      });
    });

    // Save button: persist and return to viewer
    document.querySelectorAll('.btn-save-instruction').forEach(saveButton => {
      saveButton.addEventListener('click', async function() {
        const instructionId = this.dataset.id;
        const item = this.closest('.instruction-item');
        const textarea = item.querySelector('.instruction-editor');
        const viewer = item.querySelector('.instruction-viewer');
        const viewerActions = item.querySelector('.instruction-viewer-actions');
        const editorActions = item.querySelector('.instruction-editor-actions');
        const nameElement = item.querySelector('.instruction-name');

        try {
          const instruction = await api.getUserInstruction(instructionId);
          instruction.content = textarea.value;
          const saveResponse = await api.updateUserInstruction(instruction);
          if (!saveResponse) throw new Error('Server returned failure');

          // Update viewer with saved content and return to view mode
          viewer.textContent = textarea.value;
          textarea.style.display = 'none';
          editorActions.style.display = 'none';
          viewer.style.display = 'block';
          viewerActions.style.display = 'flex';

          const successMsg = document.createElement('div');
          successMsg.className = 'instruction-save-success';
          successMsg.textContent = 'Saved successfully!';
          item.appendChild(successMsg);
          setTimeout(() => successMsg.remove(), 2000);
        } catch (error) {
          console.error('Error saving instruction:', error);
          alert('Failed to save instruction: ' + error.message);
        }
      });
    });

    // Close button: collapse panel
    document.querySelectorAll('.btn-cancel-edit').forEach(cancelButton => {
      cancelButton.addEventListener('click', function() {
        const item = this.closest('.instruction-item');
        item.querySelector('.instruction-content').style.display = 'none';
        item.querySelector('.instruction-name').classList.remove('editing');
      });
    });
  } catch (error) {
    console.error('Error loading instructions:', error);
    $id('instruction-list').innerHTML = '<div class="error">Failed to load instructions</div>';
  }
}

async function updateJiraButtonState() {
  try {
    const s = await api.getJiraSettings();
    const configured = !!(s && s.url && s.login && s.api_key);
    const title = configured ? '' : 'Configure Jira in Settings to enable';
    ['btn-jira-epic', 'btn-jira-jql'].forEach(id => {
      const btn = $id(id);
      if (!btn) return;
      btn.disabled = !configured;
      btn.title = title;
    });
  } catch (_) {}
}

function updateInstructionSelectionFeedback() {
  const count = state.selectedInstructionIds.size;
  const btn = $id('sidebar-instructions-btn');
  if (!btn) return;
  btn.textContent = count > 0 ? `Instructions (${count})` : 'Instructions';
}

// -- Editor tab -------------------------------------------------------------
const _expandedDirs = new Set(); // persists across re-renders
let _cmEditor = null;
let _autosaveTimer = null;
let _autosaveEnabled = localStorage.getItem('editor-autosave') === 'true';
let _editorTabs = [];      // { path, savedContent, draftContent, cursor, scroll, touched }
let _activeTabPath = null;
const _editorStateByTrack = new Map(); // trackId → { tabs, activeTabPath }

function _saveEditorStateForTrack(trackId) {
  if (!trackId) return;
  if (_cmEditor && _activeTabPath) {
    const t = _activeTab();
    if (t) { t.draftContent = _cmEditor.getValue(); t.cursor = _cmEditor.getCursor(); t.scroll = _cmEditor.getScrollInfo(); }
  }
  _editorStateByTrack.set(trackId, { tabs: _editorTabs, activeTabPath: _activeTabPath });
}

function _restoreEditorStateForTrack(trackId) {
  const saved = trackId ? _editorStateByTrack.get(trackId) : null;
  _editorTabs = saved ? saved.tabs : [];
  _activeTabPath = saved ? saved.activeTabPath : null;
  if (_cmEditor) {
    const tab = _activeTab();
    if (tab) {
      _cmEditor.setValue(tab.draftContent ?? tab.savedContent);
      _cmEditor.setOption('mode', _getCodeMirrorMode(tab.path));
      if (tab.cursor) _cmEditor.setCursor(tab.cursor);
      if (tab.scroll) _cmEditor.scrollTo(tab.scroll.left, tab.scroll.top);
    } else {
      _cmEditor.setValue('');
    }
  }
}

function _activeTab() {
  return _editorTabs.find(t => t.path === _activeTabPath) || null;
}

function _isTabDirty(tab) {
  if (!tab) return false;
  if (tab.path === _activeTabPath && _cmEditor)
    return _cmEditor.getValue() !== tab.savedContent;
  return tab.draftContent !== null && tab.draftContent !== tab.savedContent;
}

function _renderTabBar() {
  const bar = $id('editor-tab-bar');
  if (!bar) return;
  bar.innerHTML = '';
  for (const tab of _editorTabs) {
    const dirty = _isTabDirty(tab);
    const active = tab.path === _activeTabPath;
    const name = tab.path.split('/').pop();
    const el = document.createElement('div');
    el.className = `editor-file-tab${active ? ' active' : ''}`;
    el.title = tab.path;
    el.innerHTML = `<span class="editor-file-tab-name">${escapeHtml(name)}${dirty ? '<span class="editor-tab-dirty">●</span>' : ''}</span><span class="editor-file-tab-close">×</span>`;
    el.querySelector('.editor-file-tab-name').addEventListener('click', () => _switchFileTab(tab.path));
    el.querySelector('.editor-file-tab-close').addEventListener('click', (e) => { e.stopPropagation(); _closeFileTab(tab.path); });
    bar.appendChild(el);
  }
}

function _switchFileTab(path) {
  if (!_cmEditor || path === _activeTabPath) return;
  const cur = _activeTab();
  if (cur) {
    cur.draftContent = _cmEditor.getValue();
    cur.cursor = _cmEditor.getCursor();
    cur.scroll = _cmEditor.getScrollInfo();
  }
  _activeTabPath = path;
  const tab = _activeTab();
  if (!tab) return;
  _cmEditor.setValue(tab.draftContent ?? tab.savedContent);
  _cmEditor.setOption('mode', _getCodeMirrorMode(path));
  if (tab.cursor) _cmEditor.setCursor(tab.cursor);
  if (tab.scroll) _cmEditor.scrollTo(tab.scroll.left, tab.scroll.top);
  _cmEditor.focus();
  _renderTabBar();
  document.querySelectorAll('.file-tree-row.selected').forEach(r => r.classList.remove('selected'));
  document.querySelector(`.file-tree-row[data-path="${CSS.escape(path)}"]`)?.classList.add('selected');
}

function _closeFileTab(path) {
  const idx = _editorTabs.findIndex(t => t.path === path);
  if (idx === -1) return;
  _editorTabs.splice(idx, 1);
  if (_activeTabPath === path) {
    const next = _editorTabs[Math.min(idx, _editorTabs.length - 1)];
    if (next && _cmEditor) {
      _activeTabPath = next.path;
      _cmEditor.setValue(next.draftContent ?? next.savedContent);
      _cmEditor.setOption('mode', _getCodeMirrorMode(next.path));
      if (next.cursor) _cmEditor.setCursor(next.cursor);
      if (next.scroll) _cmEditor.scrollTo(next.scroll.left, next.scroll.top);
      document.querySelectorAll('.file-tree-row.selected').forEach(r => r.classList.remove('selected'));
      document.querySelector(`.file-tree-row[data-path="${CSS.escape(next.path)}"]`)?.classList.add('selected');
    } else {
      _activeTabPath = null;
      if (_cmEditor) _cmEditor.setValue('');
    }
  }
  _renderTabBar();
  _renderEditorHeaderActions();
}

function _renderEditorHeaderActions() {
  const headerActions = $id('plan-header-actions');
  if (!headerActions) return;
  if (!_activeTabPath) { headerActions.innerHTML = ''; return; }
  headerActions.innerHTML = `
    <span id="editor-save-status" class="editor-save-status"></span>
    <label class="editor-autosave-label">
      <input type="checkbox" id="editor-autosave-cb" ${_autosaveEnabled ? 'checked' : ''}>
      Autosave
    </label>
    <button class="btn btn-sm" id="btn-save-file">Save</button>`;
  $id('btn-save-file').addEventListener('click', saveFile);
  $id('editor-autosave-cb').addEventListener('change', (e) => {
    _autosaveEnabled = e.target.checked;
    localStorage.setItem('editor-autosave', _autosaveEnabled);
  });
}

function _getCodeMirrorMode(filePath) {
  const ext = (filePath.split('.').pop() || '').toLowerCase();
  const modes = {
    py: 'python', js: 'javascript', ts: 'javascript',
    css: 'css', html: 'htmlmixed', htm: 'htmlmixed',
    yaml: 'yaml', yml: 'yaml',
    md: 'markdown', markdown: 'markdown',
    sh: 'shell', bash: 'shell',
    json: { name: 'javascript', json: true },
  };
  return modes[ext] || 'text/plain';
}

async function renderEditor() {
  if ($id('editor-browser')) {
    // Already initialized - restore header and tab bar
    _renderEditorHeaderActions();
    _renderTabBar();
    return;
  }
  const el = $id('plan-header-actions'); if (el) el.innerHTML = '';
  const pane = $id('tab-editor');
  pane.innerHTML = `
    <div class="editor-layout">
      <div class="editor-browser" id="editor-browser"></div>
      <div class="editor-pane" id="editor-pane">
        <div class="editor-tab-bar" id="editor-tab-bar"></div>
        <div class="editor-cm-wrapper" id="editor-cm-wrapper">
          <div class="empty-state">Select a file to edit.</div>
        </div>
      </div>
    </div>`;
  await renderFileBrowser('.');
}

async function renderFileBrowser(rootPath) {
  const container = $id('editor-browser');
  if (!container) return;
  container.innerHTML = '<div class="empty-state">Loading...</div>';
  try {
    const data = await apiFetch(`/api/files/list?path=${encodeURIComponent(rootPath)}`);
    container.innerHTML = '';
    const header = document.createElement('div');
    header.className = 'file-browser-header';
    header.textContent = 'Files';
    container.appendChild(header);
    const tree = document.createElement('div');
    tree.className = 'file-tree';
    await _buildTreeNodes(tree, rootPath, data.entries, 0);
    container.appendChild(tree);
  } catch (e) {
    container.innerHTML = `<div class="empty-state">Error: ${e.message}</div>`;
  }
}

async function _buildTreeNodes(parent, dirPath, entries, depth) {
  for (const entry of entries) {
    const row = document.createElement('div');
    row.className = 'file-tree-row';
    row.style.paddingLeft = `${8 + depth * 14}px`;
    row.dataset.path = entry.path;
    row.dataset.type = entry.type;

    const icon = document.createElement('span');
    icon.className = 'file-tree-icon';

    const label = document.createElement('span');
    label.className = 'file-tree-label';
    label.textContent = entry.name;

    if (entry.type === 'dir') {
      const expanded = _expandedDirs.has(entry.path);
      icon.textContent = expanded ? '▾' : '▸';
      row.classList.add('file-tree-dir');
      row.append(icon, label);
      parent.appendChild(row);

      const childContainer = document.createElement('div');
      childContainer.className = 'file-tree-children';
      if (!expanded) childContainer.style.display = 'none';
      parent.appendChild(childContainer);

      if (expanded) {
        await _loadDirChildren(childContainer, entry.path, depth + 1);
      }

      row.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (_expandedDirs.has(entry.path)) {
          _expandedDirs.delete(entry.path);
          icon.textContent = '▸';
          childContainer.style.display = 'none';
        } else {
          _expandedDirs.add(entry.path);
          icon.textContent = '▾';
          childContainer.style.display = '';
          if (!childContainer.hasChildNodes()) {
            await _loadDirChildren(childContainer, entry.path, depth + 1);
          }
        }
      });
    } else {
      icon.textContent = '·';
      row.classList.add('file-tree-file');
      row.append(icon, label);
      parent.appendChild(row);
      row.addEventListener('click', (e) => {
        e.stopPropagation();
        // Highlight selected
        document.querySelectorAll('.file-tree-row.selected').forEach(r => r.classList.remove('selected'));
        row.classList.add('selected');
        openFile(entry.path);
      });
    }
  }
}

async function _loadDirChildren(container, dirPath, depth) {
  container.innerHTML = `<div class="file-tree-row" style="padding-left:${8 + depth * 14}px; color:var(--text-dim)">Loading...</div>`;
  try {
    const data = await apiFetch(`/api/files/list?path=${encodeURIComponent(dirPath)}`);
    container.innerHTML = '';
    await _buildTreeNodes(container, dirPath, data.entries, depth);
  } catch (e) {
    container.innerHTML = `<div class="file-tree-row" style="padding-left:${8 + depth * 14}px; color:var(--red)">${e.message}</div>`;
  }
}

async function openFile(filePath) {
  // Already open → switch
  if (_editorTabs.find(t => t.path === filePath)) {
    _switchFileTab(filePath);
    return;
  }

  const data = await apiFetch(`/api/files/read?path=${encodeURIComponent(filePath)}`);
  if (!data) { showToast(`Cannot read file: ${filePath}`); return; }

  const curTab = _activeTab();
  const curDirty = _isTabDirty(curTab);

  if (curTab && !curDirty && !curTab.touched) {
    // Replace current tab only if never modified (neither dirty nor saved after edit)
    curTab.path = filePath;
    curTab.savedContent = data.content;
    curTab.draftContent = null;
    curTab.cursor = null;
    curTab.scroll = null;
    curTab.touched = false;
    _activeTabPath = filePath;
  } else {
    // File modified (even if saved) or never opened → new tab
    if (curTab && _cmEditor) {
      curTab.draftContent = _cmEditor.getValue();
      curTab.cursor = _cmEditor.getCursor();
      curTab.scroll = _cmEditor.getScrollInfo();
    }
    _editorTabs.push({ path: filePath, savedContent: data.content, draftContent: null, cursor: null, scroll: null, touched: false });
    _activeTabPath = filePath;
  }

  const wrapper = $id('editor-cm-wrapper');
  if (!_cmEditor) {
    wrapper.innerHTML = '';
    if (typeof CodeMirror !== 'undefined') {
      _cmEditor = CodeMirror(wrapper, {
        value: data.content,
        mode: _getCodeMirrorMode(filePath),
        theme: 'dracula',
        lineNumbers: true,
        lineWrapping: false,
        tabSize: 2,
        indentWithTabs: false,
        autofocus: true,
      });
      _cmEditor.on('change', () => {
        const t = _activeTab();
        if (t) t.touched = true;
        _renderTabBar();
        if (!_autosaveEnabled) return;
        clearTimeout(_autosaveTimer);
        _autosaveTimer = setTimeout(saveFile, 1000);
      });
    } else {
      wrapper.innerHTML = `<pre class="editor-preview">${escapeHtml(data.content)}</pre>`;
    }
  } else {
    _cmEditor.setValue(data.content);
    _cmEditor.setOption('mode', _getCodeMirrorMode(filePath));
    _cmEditor.focus();
  }

  _renderTabBar();
  _renderEditorHeaderActions();
}

async function saveFile() {
  if (!_activeTabPath || !_cmEditor) return;
  const tab = _activeTab();
  const content = _cmEditor.getValue();
  const statusEl = $id('editor-save-status');
  try {
    const res = await fetch('/api/files/write', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: _activeTabPath, content }),
    });
    if (!res.ok) {
      const body = await res.text();
      console.error('saveFile failed', res.status, body);
      if (statusEl) _showSaveStatus(statusEl, `Error ${res.status}: ${body}`, 'error');
      return;
    }
    if (tab) { tab.savedContent = content; tab.draftContent = null; }
    _renderTabBar();
    if (statusEl) _showSaveStatus(statusEl, 'Saved', 'success');
  } catch (e) {
    console.error('saveFile error', e);
    if (statusEl) _showSaveStatus(statusEl, `Error: ${e.message}`, 'error');
  }
}

function _showSaveStatus(el, msg, type) {
  el.textContent = msg;
  el.className = `editor-save-status ${type}`;
  el.style.opacity = '1';
  clearTimeout(el._fadeTimeout);
  el._fadeTimeout = setTimeout(() => { el.style.opacity = '0'; }, 2000);
}

// -- Spec tab ---------------------------------------------------------------
async function renderSpec(planId) {
  const el = $id('plan-header-actions'); if (el) el.innerHTML = '';
  const pane = $id('tab-spec');
  pane.innerHTML = '<div class="empty-state">Loading...</div>';
  const [data, filesData, tasksData, phasesData] = await Promise.all([
    api.getTrackSpec(planId),
    api.getTrackFiles(planId),
    api.getTasks(planId),
    api.getPhases(planId),
  ]);
  if (!data || !data.content) {
    pane.innerHTML = '<div class="empty-state">No spec yet. Run <code>arche spec</code>.</div>';
    return;
  }
  const taskCount = (tasksData && Array.isArray(tasksData)) ? tasksData.length : 0;
  const phaseCount = (phasesData && Array.isArray(phasesData)) ? phasesData.length : 0;
  const namedPhaseCount = (phasesData && Array.isArray(phasesData))
    ? phasesData.filter(p => p && p.name && p.name.trim() !== '').length
    : 0;
  state.specTaskCount = taskCount;
  state.specPhaseCount = phaseCount;

  const trackFiles = (filesData && filesData.files) ? filesData.files : [];
  const filesListHtml = trackFiles.length > 0
    ? trackFiles.map(f => {
        const isImg = /\.(png|jpg|jpeg|gif|webp|bmp|svg)$/i.test(f);
        return `<span class="task-file-tag">${isImg ? '🖼' : '📄'} ${escHtml(f)}</span>`;
      }).join('')
    : '<span style="color:var(--text-dim);font-size:12px">No reference files.</span>';

  const hasContent = taskCount > 0 || namedPhaseCount > 0;
  const phasesDisabled = hasContent ? 'disabled' : '';
  const tasksDisabled = hasContent ? 'disabled' : '';

  pane.innerHTML = `
    <div class="spec-toolbar" id="spec-toolbar-view">
      <button class="btn-primary btn-sm" onclick="refineSpec('${planId}')">✦ Refine spec</button>
      <button class="btn-ghost btn-sm" onclick="openSpecEditor('${planId}')">✎ Edit</button>
      <button class="btn-ghost btn-sm" data-phase-count="${phaseCount}" onclick="generatePhases('${planId}')" ${phasesDisabled}>⚡ Generate phases</button>
      <button class="btn-ghost btn-sm" data-task-count="${taskCount}" onclick="generateTasks('${planId}')" ${tasksDisabled}>⚡ Generate tasks</button>
    </div>
    <div class="spec-toolbar hidden" id="spec-toolbar-edit">
      <button class="btn-primary btn-sm" onclick="saveSpecEdit('${planId}')">✓ Save</button>
      <button class="btn-ghost btn-sm" onclick="cancelSpecEdit('${planId}')">✕ Cancel</button>
    </div>
    <pre class="spec-content" id="spec-view">${escHtml(data.content)}</pre>
    <textarea class="spec-editor hidden" id="spec-edit-area">${escHtml(data.content)}</textarea>
    <div class="track-files-section">
      <div class="track-files-header">
        <span>📎 Track reference files</span>
        <button class="btn-ghost btn-sm" onclick="openTrackFilesModal('${planId}')">Edit</button>
      </div>
      <div class="track-files-list">${filesListHtml}</div>
    </div>`;
}

function openSpecEditor(planId) {
  $id('spec-toolbar-view').classList.add('hidden');
  $id('spec-toolbar-edit').classList.remove('hidden');
  $id('spec-view').classList.add('hidden');
  $id('spec-edit-area').classList.remove('hidden');
  $id('spec-edit-area').focus();
}

async function saveSpecEdit(planId) {
  const content = $id('spec-edit-area').value;
  await api.saveSpec(planId, content);
  showToast('✓ Spec saved');
  await renderSpec(planId);
}

function cancelSpecEdit(planId) {
  $id('spec-toolbar-edit').classList.add('hidden');
  $id('spec-toolbar-view').classList.remove('hidden');
  $id('spec-edit-area').classList.add('hidden');
  $id('spec-view').classList.remove('hidden');
}

async function openTrackFilesModal(planId) {
  const data = await api.getTrackFiles(planId);
  const files = (data && data.files) ? data.files : [];
  const newVal = prompt('Track reference files (one path per line):', files.join('\n'));
  if (newVal === null) return; // cancelled
  const newFiles = newVal.split('\n').map(l => l.trim()).filter(Boolean);
  await api.setTrackFiles(planId, newFiles);
  showToast('✓ Track files updated');
  await renderSpec(planId);
}

// -- Sessions tab -----------------------------------------------------------
function renderSessions(plan) {
  const el = $id('plan-header-actions'); if (el) el.innerHTML = '';
  const sessions = plan.sessions || [];
  const pane = $id('tab-sessions');

  if (sessions.length === 0) {
    pane.innerHTML = '<div class="empty-state">No sessions yet.</div>';
    return;
  }

  const items = sessions.map(date => `
    <div class="session-item">
      <div class="session-item-header" onclick="toggleSession(this, '${plan.id}', '${date}')">
        <span>📅 ${date}</span>
        <span>▸</span>
      </div>
      <div class="session-item-content" data-plan="${plan.id}" data-date="${date}">
        Loading...
      </div>
    </div>`).join('');

  pane.innerHTML = `<div class="session-list">${items}</div>`;
}

async function toggleSession(headerEl, planId, date) {
  const content = headerEl.nextElementSibling;
  const isOpen = content.classList.contains('open');

  if (!isOpen) {
    const data = await api.getSession(planId, date);
    content.textContent = data ? data.content : '(empty)';
    content.classList.add('open');
    headerEl.querySelector('span:last-child').textContent = '▾';
  } else {
    content.classList.remove('open');
    headerEl.querySelector('span:last-child').textContent = '▸';
  }
}

// -- UI task actions (action bar) --------------------------------------------
function _getUiTask() {
  const plan = state._lastPlan;
  if (!plan || !state.uiSelectedTaskId) return null;
  return (plan.tasks || []).find(t => t.id === state.uiSelectedTaskId) || null;
}

function uiRunTask() {
  const autoDone = $id('action-auto-done')?.checked ?? true;

  // If bulk selection exists, run bulk; otherwise run single task
  if (state.bulkSelectedTaskIds && state.bulkSelectedTaskIds.length > 0) {
    const bulkAgent = state.projectAgentsByPhase['dev'] || '';
    runBulkTasks(state.selectedPlanId, state.bulkSelectedTaskIds, '', autoDone, bulkAgent);
  } else {
    const t = _getUiTask();
    if (t) {
      openRunModal(state.selectedPlanId, t.id, t.title, autoDone);
    }
  }
}

async function uiStopRun() {
  if (!state.selectedPlanId) return;
  try {
    const resp = await fetch(`/api/tracks/${state.selectedPlanId}/stop-run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await resp.json();
    console.log('[uiStopRun] Stopped:', data);
    state.outputRunning = false;
    if (state.outputEventSource) {
      state.outputEventSource.close();
      state.outputEventSource = null;
    }
    refresh();
  } catch (err) {
    console.error('[uiStopRun] Error:', err);
  }
}

async function uiSelectTask() {
  const t = _getUiTask();
  if (!t || t.status === 'DONE') return;
  await api.selectTask(state.selectedPlanId, t.id);
  await renderPanelFor(state.selectedPlanId);
  await refreshSidebar();
}

function uiEditTask() {
  const t = _getUiTask();
  if (t) openEditTask(state.selectedPlanId, t.id);
}

function uiDoneTask() {
  const t = _getUiTask();
  if (t && t.status !== 'DONE') openDoneModal(state.selectedPlanId, t.id, t.title);
}

function uiBlockTask() {
  const t = _getUiTask();
  if (!t || t.status === 'DONE') return;
  openBlockModal(state.selectedPlanId, t.id, t.title);
}

function handleStatusChange(newStatus) {
  const t = _getUiTask();
  if (!t) return;

  // Convert status change to appropriate action
  if (newStatus === 'DONE') {
    openDoneModal(state.selectedPlanId, t.id, t.title);
  } else if (newStatus === 'BLOCKED') {
    openBlockModal(state.selectedPlanId, t.id, t.title);
  } else if (newStatus === 'IN_PROGRESS') {
    // Just select the task (it will be marked IN_PROGRESS when running)
    uiSelectTask();
  } else if (newStatus === 'TODO') {
    // Reset to TODO - could add a confirmation here
    markTaskTodo(state.selectedPlanId, t.id);
  }
}

async function markTaskTodo(planId, taskId) {
  await api.updateTask(planId, taskId, { status: 'TODO' });
  await renderPanelFor(planId);
  await refreshSidebar();
}

async function handleTaskStatusChange(planId, taskId, newStatus, title = '') {
  if (newStatus === 'DONE') {
    openDoneModal(planId, taskId, title);
  } else if (newStatus === 'BLOCKED') {
    openBlockModal(planId, taskId, title);
  } else if (newStatus === 'TODO') {
    await markTaskTodo(planId, taskId);
  } else if (newStatus === 'IN_PROGRESS') {
    await api.updateTask(planId, taskId, { status: 'IN_PROGRESS' });
    await renderPanelFor(planId);
    await refreshSidebar();
  }
}

// -- Legacy actions -----------------------------------------------------------
async function markTaskDone(planId, taskId) {
  await api.doneTask(planId, taskId);
  await renderPanelFor(planId);
  await refreshSidebar();
}

async function markTaskBlocked(planId, taskId) {
  const reason = prompt('Reason for blocking:');
  if (!reason) return;
  await api.blockTask(planId, taskId, reason);
  await renderPanelFor(planId);
}

async function switchCurrentTask(planId, taskId) {
  await api.selectTask(planId, taskId);
  await renderPanelFor(planId);
  await refreshSidebar();
}

// -- Run task modal ----------------------------------------------------------
async function openRunModal(trackId, taskId, taskTitle, autoDone = true) {
  state.runTask = { trackId, taskId };
  $id('run-task-title').textContent = taskTitle;
  $id('run-task-comment').value = '';
  $id('run-task-auto-done').checked = autoDone;

  // Populate agent selector
  const sel = $id('run-task-agent');
  sel.innerHTML = '<option value="">— none —</option>';
  try {
    const data = await api.listAgents();
    if (data && data.agents) {
      data.agents.forEach(a => {
        const opt = document.createElement('option');
        opt.value = a.id;
        opt.textContent = a.name + (a.role ? ` (${a.role})` : '');
        sel.appendChild(opt);
      });
    }
    // Pre-select agent configured for the "dev" phase
    const devAgent = state.projectAgentsByPhase['dev'];
    if (devAgent) sel.value = devAgent;
  } catch (_) {}

  $id('modal-run-overlay').classList.remove('hidden');
  setTimeout(() => $id('run-task-comment').focus(), 50);
}

function closeRunModal() {
  $id('modal-run-overlay').classList.add('hidden');
  state.runTask = null;
}

function confirmRunTask() {
  if (!state.runTask) return;
  const { trackId, taskId } = state.runTask;
  const comment = $id('run-task-comment').value.trim();
  const autoDone = $id('run-task-auto-done').checked;
  const agentId = $id('run-task-agent').value;
  closeRunModal();
  runTask(trackId, taskId, comment, autoDone, agentId);
}

// -- Streaming helpers -------------------------------------------------------
function _switchToOutputTab() {
  // Output is now in the terminals section - ensure console is open
  if (state.consoleCollapsed) {
    $id('console-wrapper').classList.remove('collapsed');
    state.consoleCollapsed = false;
    $id('btn-console-toggle').textContent = '−';
  }
}

function _appendOutput(text) {
  state.outputText += text;
  if (state._outputTerminal) {
    state._outputTerminal.term.write(text.replace(/\r?\n/g, '\r\n'));
  }
}

function _setOutputHeader(title) {
  if (state._outputTerminal) {
    state._outputTerminal.term.write(`\x1b[1m${title}\x1b[0m\r\n`);
  }
}

/** Create (or reuse+clear) a streaming terminal for generation operations. */
function _openOutputTerminal(opId, title) {
  if (state.consoleCollapsed) {
    $id('console-wrapper').classList.remove('collapsed');
    state.consoleCollapsed = false;
    $id('btn-console-toggle').textContent = '−';
  }
  const id = `-gen-${opId}`;
  const existing = state.terminals.find(t => t.id === id);
  if (existing) {
    try { existing.term.clear(); } catch (_) {}
    selectTerminal(id);
    renderTerminalTabs();
    state._outputTerminal = existing;
    return existing;
  }
  const pane = document.createElement('div');
  pane.className = 'terminal-pane';
  pane.id = `term-pane-${id}`;
  $id('terminal-container').appendChild(pane);
  const term = new Terminal(TERM_OPTS);
  const fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open(pane);
  const entry = { id, term, fitAddon, ws: null, pane, taskTitle: title };
  state.terminals.push(entry);
  selectTerminal(id);
  renderTerminalTabs();
  state._outputTerminal = entry;
  return entry;
}

/** Start an SSE stream (GET). Callbacks: onMeta, onText, onDone, onError, onSignal */
function _startStream(url, { onMeta, onText, onDone, onError, onSignal } = {}) {
  if (state.outputEventSource) {
    state.outputEventSource.close();
    state.outputEventSource = null;
  }
  const es = new EventSource(url);
  state.outputEventSource = es;

  es.onmessage = (evt) => {
    const data = evt.data;
    if (data === '__DONE__') {
      es.close();
      state.outputEventSource = null;
      if (onDone) onDone();
      return;
    }
    if (data.startsWith('__META__ ')) {
      if (onMeta) onMeta(data.slice(9));
      return;
    }
    if (/^__[A-Z_]+__$/.test(data)) {
      if (onSignal) onSignal(data);
      return;
    }
    if (onText) onText(stripAnsi(data));
  };

  es.onerror = () => {
    es.close();
    state.outputEventSource = null;
    if (onError) onError();
  };
  return es;
}

/** Start an SSE stream over POST. Same callbacks as _startStream. */
async function _startPostStream(url, body, { onMeta, onText, onDone, onError, onSignal } = {}) {
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) { if (onError) onError(); return; }

    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    let finished = false;

    while (!finished) {
      const { done: streamDone, value } = await reader.read();
      if (streamDone) break;

      buf += dec.decode(value, { stream: true });

      let boundary;
      while ((boundary = buf.indexOf('\n\n')) !== -1) {
        const msg = buf.slice(0, boundary);
        buf = buf.slice(boundary + 2);
        if (!msg.trim()) continue;

        const dataLines = msg.split('\n').filter(l => l.startsWith('data: ')).map(l => l.slice(6));
        if (dataLines.length === 0) continue;
        const data = dataLines.join('\n');

        if (data === '__DONE__') { finished = true; if (onDone) onDone(); break; }
        if (data.startsWith('__META__ ')) { if (onMeta) onMeta(data.slice(9)); continue; }
        if (/^__[A-Z_]+__$/.test(data)) { if (onSignal) onSignal(data); continue; }
        if (onText) onText(stripAnsi(data));
      }
    }
  } catch (e) {
    if (onError) onError();
  }
}

// -- Run task / Output tab ---------------------------------------------------

// Returns the track name to use as terminal tab title.
function _getTerminalTitle(planId) {
  const plan = state._lastPlan;
  if (plan && plan.name) return plan.name;
  if (plan && plan.id) return plan.id;
  return planId || 'Task';
}

async function runTask(planId, taskId, comment = '', autoDone = true, agentId = '') {
  if (state.outputEventSource) {
    state.outputEventSource.close();
    state.outputEventSource = null;
  }

  state.outputRunning = true;

  const tabTitle = _getTerminalTitle(planId);

  try {
    const params = new URLSearchParams();
    if (comment) params.append('comment', comment);
    if (autoDone) params.append('auto_done', 'true');
    
    // Add selected instruction IDs if any
    if (state.selectedInstructionIds && state.selectedInstructionIds.size > 0) {
      params.append('instructions', Array.from(state.selectedInstructionIds).join(','));
    }

    // Add selected agent if any
    if (agentId) params.append('agent_id', agentId);

    // Prepare the task server-side: switch to task, build prompt, save to temp file
    const resp = await fetch(`/api/tracks/${planId}/tasks/${taskId}/prepare-run?${params}`);
    if (!resp.ok) {
      const err = await resp.text();
      console.error('[runTask] Error preparing task:', err);
      state.outputRunning = false;
      return;
    }

    const { token } = await resp.json();

    // Open a real interactive PTY terminal with the command injected via token
    createTaskTerminal(taskId, tabTitle, token);
    state.outputRunning = false;
    refresh();
  } catch (e) {
    console.error('[runTask] Error:', e);
    state.outputRunning = false;
  }
}

function runBulkTasks(trackId, taskIds, comment = '', autoDone = true, agentId = '') {
  if (state.outputEventSource) {
    state.outputEventSource.close();
    state.outputEventSource = null;
  }

  state.outputText = '';
  state.outputRunning = true;
  state._outputMeta = '';
  state._outputDone = false;

  // Single terminal for all bulk tasks - tab name = track name
  const bulkTabTitle = _getTerminalTitle(trackId);
  const bulkTerminal = createStreamTerminal(`bulk-${trackId}`, bulkTabTitle);
  bulkTerminal.term.clear();

  const payload = {
    task_ids: taskIds,
    comment: comment,
    auto_done: autoDone,
    instructions: state.selectedInstructionIds && state.selectedInstructionIds.size > 0
      ? Array.from(state.selectedInstructionIds).join(',')
      : '',
    agent_id: agentId || '',
  };

  const url = `/api/tracks/${trackId}/tasks/bulk-run`;

  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).then(response => {
    if (!response.ok) {
      bulkTerminal.term.write(`\n⚠ Error: ${response.statusText}\n`);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const processStream = async () => {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            state.outputRunning = false;
            state._outputDone = true;
            refresh();
            return;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';

          for (const block of lines) {
            if (!block.trim()) continue;
            // Reassemble multi-line SSE block: each line may start with "data: "
            const dataLines = block.split('\n')
              .filter(l => l.startsWith('data: ') || l === 'data:')
              .map(l => l.startsWith('data: ') ? l.slice(6) : '');
            if (dataLines.length === 0) continue;
            const data = dataLines.join('\n');

              if (data.startsWith('__BULK_DONE__')) {
                state.outputRunning = false;
                state._outputDone = true;
                state.bulkSelectedTaskIds = [];
                bulkTerminal.term.write('\r\n✓ Bulk execution complete\r\n');
                await refresh();
                if (state.selectedPlanId) await renderPanelFor(state.selectedPlanId);
                return;
              }

              if (data.startsWith('__TASK_START__')) {
                const taskInfo = data.slice(14).trim();
                const match = taskInfo.match(/^(\d+)\/\d+\s+(.*)$/);
                if (match) {
                  bulkTerminal.term.write(`\r\n━━ ${match[1]}. ${match[2]} ━━\r\n\r\n`);
                }
                continue;
              }

              if (data.startsWith('__TASK_DONE__')) {
                bulkTerminal.term.write('\r\n✓ Task complete\r\n\r\n');
                continue;
              }

              const chunk = stripAnsi(data).replace(/\r?\n/g, '\r\n');
              state.outputText += chunk;
              bulkTerminal.term.write(chunk);
          }
        }
      } catch (err) {
        bulkTerminal.term.write(`\n⚠ Stream error: ${err.message}\n`);
      }
    };

    processStream();
  }).catch(err => {
    bulkTerminal.term.write(`\n⚠ Network error: ${err.message}\n`);
  });
}

function renderOutputPane() {
  // Output is now displayed in dedicated task terminals in the terminals section.
  // This function is kept for backward compatibility but does nothing.
}

// -- Edit task modal ---------------------------------------------------------
function openEditTask(planId, taskId) {
  const plan = state.plans.find(p => p.id === planId);
  const tasks = plan ? (plan.tasks || []) : [];
  let task = tasks.find(t => t.id === taskId);
  if (!task) {
    // Try fetching from already loaded panel data
    const panelPlan = state._lastPlan;
    task = panelPlan && (panelPlan.tasks || []).find(t => t.id === taskId);
  }
  if (!task) return;

  state.editingTask = { planId, task };
  $id('edit-task-title').value = task.title || '';
  $id('edit-task-desc').value = task.description || '';
  $id('edit-task-notes').value = task.notes || '';
  $id('edit-task-files').value = (task.files || []).join('\n');
  $id('modal-edit-overlay').classList.remove('hidden');
  $id('edit-task-title').focus();
}

function closeEditModal() {
  $id('modal-edit-overlay').classList.add('hidden');
  state.editingTask = null;
}

async function saveEditTask() {
  if (!state.editingTask) return;
  const { planId, task } = state.editingTask;
  const filesRaw = $id('edit-task-files').value.trim();
  const files = filesRaw ? filesRaw.split('\n').map(l => l.trim()).filter(Boolean) : [];
  const updates = {
    title: $id('edit-task-title').value.trim(),
    description: $id('edit-task-desc').value.trim(),
    notes: $id('edit-task-notes').value.trim(),
    files,
  };
  closeEditModal();
  await api.updateTask(planId, task.id, updates);
  await renderPanelFor(planId);
}

// -- Complete task modal -----------------------------------------------------
function openDoneModal(planId, taskId, title) {
  state.doneTask = { planId, taskId };
  $id('done-task-title').textContent = title;
  $id('done-task-notes').value = '';
  $id('modal-done-overlay').classList.remove('hidden');
  $id('done-task-notes').focus();
}

function closeDoneModal() {
  $id('modal-done-overlay').classList.add('hidden');
  state.doneTask = null;
}

async function confirmDoneTask() {
  if (!state.doneTask) return;
  const { planId, taskId } = state.doneTask;
  const notes = $id('done-task-notes').value.trim();
  closeDoneModal();
  const result = await api.doneTask(planId, taskId, notes);
  if (!result || result.message) {
    showToast(result && result.message ? result.message : 'Failed to mark task done');
  }
  await renderPanelFor(planId);
  await refreshSidebar();
}

// -- Block task modal ---------------------------------------------------------
function openBlockModal(planId, taskId, title) {
  state.blockTask = { planId, taskId };
  $id('block-task-title').textContent = title;
  $id('block-task-reason').value = '';
  $id('modal-block-overlay').classList.remove('hidden');
  $id('block-task-reason').focus();
}

function closeBlockModal() {
  $id('modal-block-overlay').classList.add('hidden');
  state.blockTask = null;
}

async function confirmBlockTask() {
  if (!state.blockTask) return;
  const reason = $id('block-task-reason').value.trim();
  if (!reason) { $id('block-task-reason').focus(); return; }
  const { planId, taskId } = state.blockTask;
  closeBlockModal();
  const result = await api.blockTask(planId, taskId, reason);
  if (!result || result.message) {
    showToast(result && result.message ? result.message : 'Failed to block task');
  }
  await renderPanelFor(planId);
  await refreshSidebar();
}

async function switchToPlan(planId) {
  await api.switchTrack(planId);
  state.selectedPlanId = planId;
  await refresh();
}

async function refreshSidebar() {
  const plans = await api.getTracks();
  if (plans) {
    state.plans = plans;
    renderSidebar(plans);
  }
}

// -- Tabs -------------------------------------------------------------------
function setupTabs() {
  document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', async () => {
      document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');

      const tab = btn.dataset.tab;
      state.activeTab = tab;
      $id(`tab-${tab}`).classList.add('active');

      if (state.selectedPlanId) {
        const plan = await api.getTrack(state.selectedPlanId);
        if (plan) await renderTabContent(plan, tab);
      }
    });
  });
}

// -- Terminal management ----------------------------------------------------
const TERM_OPTS = {
  theme: { background: '#0d0d0d', foreground: '#e0e0e0', cursor: '#39c5cf', selection: '#2a4a5a' },
  fontSize: 12,
  fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
  cursorBlink: true,
  allowTransparency: true,
  scrollback: 1000,
  wordWrap: true,
};

function setupTerminal() {
  addTerminal();
  // Observe container size changes to fit active terminal
  const resizeObserver = new ResizeObserver(() => _fitActive());
  resizeObserver.observe($id('terminal-container'));
}

function addTerminal() {
  if (state.consoleCollapsed) {
    $id('console-wrapper').classList.remove('collapsed');
    state.consoleCollapsed = false;
    $id('btn-console-toggle').textContent = '−';
  }
  _termCounter++;
  const id = `t${_termCounter}`;

  // Create pane div inside the shared container
  const pane = document.createElement('div');
  pane.className = 'terminal-pane';
  pane.id = `term-pane-${id}`;
  $id('terminal-container').appendChild(pane);

  const term = new Terminal(TERM_OPTS);
  const fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open(pane);

  const ws = _connectTerminalWs(id, term, fitAddon);
  const entry = { id, term, fitAddon, ws, pane };
  state.terminals.push(entry);

  selectTerminal(id);
  renderTerminalTabs();
  return entry;
}

// Creates an interactive PTY terminal for a task (used by runTask).
// Pass a token returned by /api/.../prepare-run to auto-inject the command.
function createTaskTerminal(taskId, taskTitle = '', token = null) {
  if (state.consoleCollapsed) {
    $id('console-wrapper').classList.remove('collapsed');
    state.consoleCollapsed = false;
    $id('btn-console-toggle').textContent = '−';
  }

  const id = `-task-${taskId}`;

  // If terminal already exists, close the old one and recreate (for re-runs)
  const existing = state.terminals.find(t => t.id === id);
  if (existing) {
    try { if (existing.ws && existing.ws.readyState === WebSocket.OPEN) existing.ws.close(); } catch (_) {}
    try { existing.term.dispose(); } catch (_) {}
    existing.pane.remove();
    state.terminals.splice(state.terminals.indexOf(existing), 1);
  }

  const titleWords = taskTitle.split(/\s+/).slice(0, 4).join(' ');
  const displayTitle = titleWords || taskId;

  const pane = document.createElement('div');
  pane.className = 'terminal-pane';
  pane.id = `term-pane-${id}`;
  $id('terminal-container').appendChild(pane);

  // Force synchronous reflow so the container has correct dimensions before xterm.js
  // measures character size (xterm caches charWidth at open() time; if the container
  // was display:none it would cache 0 and fitAddon.fit() would never fix it).
  void $id('terminal-container').offsetWidth;

  const term = new Terminal(TERM_OPTS);
  const fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open(pane);

  // Real PTY WebSocket - the user can interact with the LLM if it asks questions
  const ws = _connectTerminalWs(id, term, fitAddon, token);
  const entry = { id, term, fitAddon, ws, pane, taskTitle: displayTitle };
  state.terminals.push(entry);

  selectTerminal(id);
  renderTerminalTabs();
  // Extra delayed fit to handle cases where console was just uncollapsed
  setTimeout(() => { try { fitAddon.fit(); } catch (_) {} }, 200);
  return entry;
}

// Creates a streaming-only terminal for bulk task runs (no PTY WebSocket).
function createStreamTerminal(taskId, taskTitle = '') {
  if (state.consoleCollapsed) {
    $id('console-wrapper').classList.remove('collapsed');
    state.consoleCollapsed = false;
    $id('btn-console-toggle').textContent = '−';
  }

  const id = `-task-${taskId}`;

  const existing = state.terminals.find(t => t.id === id);
  if (existing) {
    selectTerminal(id);
    renderTerminalTabs();
    return existing;
  }

  const titleWords = taskTitle.split(/\s+/).slice(0, 4).join(' ');
  const displayTitle = titleWords || taskId;

  const pane = document.createElement('div');
  pane.className = 'terminal-pane';
  pane.id = `term-pane-${id}`;
  $id('terminal-container').appendChild(pane);

  // Force synchronous reflow so the container has correct dimensions before xterm.js
  // measures character size (xterm caches charWidth at open() time; if the container
  // was display:none it would cache 0 and fitAddon.fit() would never fix it).
  void $id('terminal-container').offsetWidth;

  const term = new Terminal(TERM_OPTS);
  const fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open(pane);

  const entry = { id, term, fitAddon, ws: null, pane, taskTitle: displayTitle };
  state.terminals.push(entry);

  selectTerminal(id);
  renderTerminalTabs();
  // Extra delayed fit to handle cases where console was just uncollapsed
  setTimeout(() => { try { fitAddon.fit(); } catch (_) {} }, 200);
  return entry;
}

function removeTerminal(id) {
  if (state.terminals.length <= 1) return; // minimum 1
  const idx = state.terminals.findIndex(t => t.id === id);
  if (idx === -1) return;

  const entry = state.terminals[idx];
  try { if (entry.ws.readyState === WebSocket.OPEN) entry.ws.close(); } catch (_) {}
  try { entry.term.dispose(); } catch (_) {}
  entry.pane.remove();
  state.terminals.splice(idx, 1);

  if (state.activeTerminalId === id) {
    const next = state.terminals[Math.min(idx, state.terminals.length - 1)];
    selectTerminal(next.id);
  } else {
    renderTerminalTabs();
  }
}

function selectTerminal(id) {
  state.activeTerminalId = id;
  state.terminals.forEach(t => { t.pane.style.display = t.id === id ? '' : 'none'; });
  renderTerminalTabs();
  if (!state.consoleCollapsed) setTimeout(() => _fitActive(), 30);
}

function renderTerminalTabs() {
  const tabs = $id('terminal-tabs');
  const canClose = state.terminals.length > 1;
  tabs.innerHTML = state.terminals.map(t => {
    // Display name: task title (first 4 words) for -task-* or Term N for regular terminals
    const displayName = t.taskTitle ? t.taskTitle : `Term&nbsp;${t.id.slice(1)}`;
    return `
    <button class="term-tab ${t.id === state.activeTerminalId ? 'active' : ''}"
            onclick="selectTerminal('${t.id}')">
      ${displayName}
      ${canClose ? `<span class="term-tab-close" onclick="event.stopPropagation();removeTerminal('${t.id}')">×</span>` : ''}
    </button>`;
  }).join('') +
    `<button class="term-tab-add" onclick="addTerminal()" title="New terminal">+</button>`;
}

function _fitActive() {
  const entry = state.terminals.find(t => t.id === state.activeTerminalId);
  if (entry) try { entry.fitAddon.fit(); } catch (_) {}
}

function _updateStatus(cls) {
  const el = $id('console-status');
  if (el) el.className = `console-status ${cls}`;
}

function _connectTerminalWs(id, term, fitAddon, token = null) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const cols = term.cols || 220;
  const rows = term.rows || 50;
  const sizeParams = `cols=${cols}&rows=${rows}`;
  const url = token
    ? `${proto}://${location.host}/ws/terminal?token=${encodeURIComponent(token)}&${sizeParams}`
    : `${proto}://${location.host}/ws/terminal?${sizeParams}`;
  const ws = new WebSocket(url);
  ws.binaryType = 'arraybuffer';

  const sendResize = (cols, rows) => {
    if (ws.readyState === WebSocket.OPEN)
      ws.send(JSON.stringify({ type: 'resize', cols, rows }));
  };

  ws.onopen = () => {
    if (id === state.activeTerminalId) _updateStatus('connected');
    try { fitAddon.fit(); } catch (_) {}
    // Always send current size explicitly - fitAddon.fit() only triggers term.onResize
    // when the size actually changes; if the terminal was already fitted before the WS
    // opened, onResize won't fire and the server PTY would stay at its default 80×24.
    sendResize(term.cols, term.rows);
  };
  ws.onmessage = (evt) => {
    const data = evt.data instanceof ArrayBuffer ? new Uint8Array(evt.data) : evt.data;
    term.write(data);
  };
  ws.onclose = () => {
    if (id === state.activeTerminalId) _updateStatus('');
    term.write('\r\n\x1b[33m[disconnected]\x1b[0m\r\n');
  };
  ws.onerror = () => {
    if (id === state.activeTerminalId) _updateStatus('error');
    term.write('\r\n\x1b[31m[ws error]\x1b[0m\r\n');
  };
  term.onData(data => {
    if (ws.readyState === WebSocket.OPEN) ws.send(new TextEncoder().encode(data));
  });
  // Send terminal dimensions to server whenever xterm.js is resized (fitAddon.fit() triggers this)
  term.onResize(({ cols, rows }) => sendResize(cols, rows));

  return ws;
}

// -- Event listeners --------------------------------------------------------
function setupEventListeners() {
  setupTabs();

  // Sidebar toggle
  const sidebarToggle = $id('sidebar-toggle');
  const sidebar = $id('sidebar');
  const sidebarCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
  if (sidebarCollapsed) { sidebar.classList.add('collapsed'); sidebarToggle.classList.add('collapsed'); }
  sidebarToggle.addEventListener('click', () => {
    const collapsed = sidebar.classList.toggle('collapsed');
    sidebarToggle.classList.toggle('collapsed', collapsed);
    localStorage.setItem('sidebar-collapsed', collapsed);
  });

  // Collapsible sidebar sections
  const sidebarSectionState = {
    'sidebar-section-tracks': false,
    'sidebar-section-customisation': false,
  };

  function toggleSection(sectionId) {
    const section = $id(sectionId);
    if (!section) return;
    const collapsed = section.classList.toggle('sidebar-section--collapsed');
    sidebarSectionState[sectionId] = collapsed;
    localStorage.setItem(`arche-sidebar-section-${sectionId}-collapsed`, collapsed);
  }

  function initSidebarSection(sectionId) {
    const section = $id(sectionId);
    if (!section) return;
    const wasCollapsed = localStorage.getItem(`arche-sidebar-section-${sectionId}-collapsed`) === 'true';
    if (wasCollapsed) section.classList.add('sidebar-section--collapsed');
    sidebarSectionState[sectionId] = wasCollapsed;
    section.querySelector('.sidebar-section-header').addEventListener('click', () => toggleSection(sectionId));
  }
  initSidebarSection('sidebar-section-customisation');
  initSidebarSection('sidebar-section-tracks');

  // Instructions sidebar button
  $id('sidebar-instructions-btn').addEventListener('click', async () => {
    const instrPanel = $id('instructions-panel');
    const isShowing = instrPanel.classList.contains('visible');
    if (isShowing) {
      toggleInstructionsView(false);
    } else {
      toggleInstructionsView(true);
      await renderInstructions();
    }
  });

  // Agents sidebar button
  $id('sidebar-agents-btn').addEventListener('click', async () => {
    const agentsPanel = $id('agents-panel');
    const isShowing = agentsPanel.classList.contains('visible');
    if (isShowing) {
      toggleAgentsView(false);
    } else {
      toggleAgentsView(true);
      await renderAgents();
    }
  });

  // New plan button
  $id('btn-new-plan').addEventListener('click', () => {
    selectTrackType('feature');
    $id('modal-overlay').classList.remove('hidden');
    $id('modal-plan-name').focus();
  });

  // Jira JQL import button
  $id('btn-jira-jql').addEventListener('click', openJiraJqlModal);
  $id('modal-jira-jql-cancel').addEventListener('click', closeJiraJqlModal);
  $id('modal-jira-jql-overlay').addEventListener('click', (e) => {
    if (e.target === $id('modal-jira-jql-overlay')) closeJiraJqlModal();
  });
  $id('modal-jira-jql-test').addEventListener('click', testJiraJql);
  $id('modal-jira-jql-import').addEventListener('click', importJiraJql);
  $id('jira-jql-query').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') testJiraJql();
    if (e.key === 'Escape') closeJiraJqlModal();
  });

  // Jira Epic import button
  $id('btn-jira-epic').addEventListener('click', openJiraEpicModal);
  $id('modal-jira-cancel').addEventListener('click', closeJiraEpicModal);
  $id('modal-jira-overlay').addEventListener('click', (e) => {
    if (e.target === $id('modal-jira-overlay')) closeJiraEpicModal();
  });
  $id('modal-jira-import').addEventListener('click', importJiraEpic);
  $id('jira-epic-key').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') importJiraEpic();
    if (e.key === 'Escape') closeJiraEpicModal();
  });

  // Modal cancel
  $id('modal-cancel').addEventListener('click', closeModal);
  $id('modal-overlay').addEventListener('click', (e) => {
    if (e.target === $id('modal-overlay')) closeModal();
  });

  // Modal create
  $id('modal-create').addEventListener('click', () => createPlan(true));
  $id('modal-create-phases').addEventListener('click', () => createPlan('phases'));
  $id('modal-create-only').addEventListener('click', () => createPlan(false));
  $id('modal-plan-name').addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });

  // Edit task modal
  $id('edit-cancel').addEventListener('click', closeEditModal);
  $id('modal-edit-overlay').addEventListener('click', (e) => { if (e.target === $id('modal-edit-overlay')) closeEditModal(); });
  $id('edit-save').addEventListener('click', saveEditTask);
  $id('edit-task-title').addEventListener('keydown', (e) => { if (e.key === 'Enter') saveEditTask(); if (e.key === 'Escape') closeEditModal(); });

  // Done task modal
  $id('done-cancel').addEventListener('click', closeDoneModal);
  $id('modal-done-overlay').addEventListener('click', (e) => { if (e.target === $id('modal-done-overlay')) closeDoneModal(); });
  $id('done-confirm').addEventListener('click', confirmDoneTask);
  $id('done-task-notes').addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.ctrlKey) confirmDoneTask(); if (e.key === 'Escape') closeDoneModal(); });

  // Block task modal
  $id('block-cancel').addEventListener('click', closeBlockModal);
  $id('modal-block-overlay').addEventListener('click', (e) => { if (e.target === $id('modal-block-overlay')) closeBlockModal(); });
  $id('block-confirm').addEventListener('click', confirmBlockTask);
  $id('block-task-reason').addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.ctrlKey) confirmBlockTask(); if (e.key === 'Escape') closeBlockModal(); });

  // Run task modal
  $id('run-cancel').addEventListener('click', closeRunModal);
  $id('modal-run-overlay').addEventListener('click', (e) => { if (e.target === $id('modal-run-overlay')) closeRunModal(); });
  $id('run-confirm').addEventListener('click', confirmRunTask);
  $id('run-task-comment').addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.ctrlKey) confirmRunTask(); if (e.key === 'Escape') closeRunModal(); });

  // Add task modal
  $id('add-task-cancel').addEventListener('click', closeAddTaskModal);
  $id('modal-add-task-overlay').addEventListener('click', (e) => { if (e.target === $id('modal-add-task-overlay')) closeAddTaskModal(); });
  $id('add-task-confirm').addEventListener('click', confirmAddTask);
  $id('add-task-title').addEventListener('keydown', (e) => { if (e.key === 'Enter') confirmAddTask(); if (e.key === 'Escape') closeAddTaskModal(); });

  // Phase modal
  $id('phase-cancel').addEventListener('click', closePhaseModal);
  $id('modal-phase-overlay').addEventListener('click', (e) => { if (e.target === $id('modal-phase-overlay')) closePhaseModal(); });
  $id('phase-create').addEventListener('click', confirmNewPhase);
  $id('modal-phase-name').addEventListener('keydown', (e) => { if (e.key === 'Enter') confirmNewPhase(); if (e.key === 'Escape') closePhaseModal(); });

  // Refresh button
  // Settings cog dropdown
  $id('btn-settings-cog').addEventListener('click', (e) => {
    e.stopPropagation();
    $id('settings-dropdown').classList.toggle('hidden');
  });
  document.addEventListener('click', () => {
    $id('settings-dropdown').classList.add('hidden');
  });
  $id('drop-archi').addEventListener('click', () => { $id('settings-dropdown').classList.add('hidden'); openArchiModal(); });
  $id('drop-memory').addEventListener('click', () => { $id('settings-dropdown').classList.add('hidden'); openMemoryModal(); });
  $id('drop-theme').addEventListener('click', () => { $id('settings-dropdown').classList.add('hidden'); openThemeModal(); });
  $id('btn-lock').addEventListener('click', toggleLockSession);
  $id('drop-project-settings').addEventListener('click', () => { $id('settings-dropdown').classList.add('hidden'); openSettingsModal(); });

  // Archi modal
  $id('archi-close').addEventListener('click', closeArchiModal);
  $id('archi-scan').addEventListener('click', runArcheScan);
  $id('modal-archi-overlay').addEventListener('click', (e) => {
    if (e.target === $id('modal-archi-overlay')) closeArchiModal();
  });

  // Memory modal
  $id('memory-close').addEventListener('click', closeMemoryModal);
  $id('memory-clear').addEventListener('click', clearMemory);
  $id('modal-memory-overlay').addEventListener('click', (e) => {
    if (e.target === $id('modal-memory-overlay')) closeMemoryModal();
  });

  // Docs button
  $id('btn-docs').addEventListener('click', () => $id('modal-docs-overlay').classList.remove('hidden'));
  $id('docs-close').addEventListener('click', () => $id('modal-docs-overlay').classList.add('hidden'));
  $id('modal-docs-overlay').addEventListener('click', (e) => {
    if (e.target === $id('modal-docs-overlay')) $id('modal-docs-overlay').classList.add('hidden');
  });

  // Console toggle
  $id('btn-console-toggle').addEventListener('click', () => {
    const wrapper = $id('console-wrapper');
    const btn = $id('btn-console-toggle');
    state.consoleCollapsed = !state.consoleCollapsed;
    wrapper.classList.toggle('collapsed', state.consoleCollapsed);
    btn.textContent = state.consoleCollapsed ? '+' : '−';
    if (!state.consoleCollapsed) setTimeout(() => _fitActive(), 50);
  });

  // Theme
  _initThemeListeners();

  // Settings modal close
  $id('settings-close').addEventListener('click', closeSettingsModal);
  $id('settings-cancel').addEventListener('click', closeSettingsModal);
  $id('modal-settings-overlay').addEventListener('click', (e) => {
    if (e.target === $id('modal-settings-overlay')) closeSettingsModal();
  });
  $id('settings-save').addEventListener('click', saveSettings);
  // Settings tabs
  document.querySelectorAll('.settings-tab').forEach(btn => {
    btn.addEventListener('click', () => _switchSettingsTab(btn.dataset.tab));
  });

  // Lock Setup Modal
  $id('lock-setup-password-toggle').addEventListener('click', () => {
    const input = $id('lock-setup-password-input');
    const btn = $id('lock-setup-password-toggle');
    if (input.type === 'password') {
      input.type = 'text';
      btn.textContent = '👁‍🗨';
    } else {
      input.type = 'password';
      btn.textContent = '👁';
    }
  });
  $id('lock-setup-confirm').addEventListener('click', async () => {
    const password = $id('lock-setup-password-input').value;
    await saveLockPassword(password);
  });
  $id('lock-setup-cancel').addEventListener('click', closeLockSetupModal);
  $id('lock-setup-password-input').addEventListener('keypress', async (e) => {
    if (e.key === 'Enter') {
      const password = $id('lock-setup-password-input').value;
      await saveLockPassword(password);
    }
  });

  // Lock Screen Modal
  $id('lock-screen-password-toggle').addEventListener('click', () => {
    const input = $id('lock-screen-password-input');
    const btn = $id('lock-screen-password-toggle');
    if (input.type === 'password') {
      input.type = 'text';
      btn.textContent = '👁‍🗨';
    } else {
      input.type = 'password';
      btn.textContent = '👁';
    }
  });
  $id('lock-screen-unlock').addEventListener('click', async () => {
    const password = $id('lock-screen-password-input').value;
    await verifyPasswordAndUnlock(password);
  });
  $id('lock-screen-password-input').addEventListener('keypress', async (e) => {
    if (e.key === 'Enter') {
      const password = $id('lock-screen-password-input').value;
      await verifyPasswordAndUnlock(password);
    }
  });

  // Settings Security tab - password input
  const settingsPasswordToggle = $id('settings-password-toggle');
  if (settingsPasswordToggle) {
    settingsPasswordToggle.addEventListener('click', () => {
      const input = $id('settings-password-input');
      const btn = $id('settings-password-toggle');
      if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '👁‍🗨';
      } else {
        input.type = 'password';
        btn.textContent = '👁';
      }
    });
  }
}

function selectTrackType(type) {
  state.newTrackType = type;
  document.querySelectorAll('.type-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.type === type);
  });
  $id('modal-feature-fields').classList.toggle('hidden', type !== 'feature');
  $id('modal-task-fields').classList.toggle('hidden', type !== 'task');
  $id('modal-debug-fields').classList.toggle('hidden', type !== 'debug');
}

function closeModal() {
  $id('modal-overlay').classList.add('hidden');
  ['modal-plan-name','spec-goal','spec-context','spec-requirements','spec-constraints','spec-out-of-scope',
   'task-description','debug-description']
    .forEach(id => { const el = $id(id); if (el) el.value = ''; });
  ['task-subtype-test','task-subtype-doc','debug-subtype-regression']
    .forEach(id => { const el = $id(id); if (el) el.checked = false; });
  selectTrackType('feature');
}

let _jiraImportES = null;

function _resetJiraModal() {
  $id('jira-epic-key').value = '';
  const status = $id('jira-import-status');
  status.textContent = '';
  status.className = 'jira-status';
  const progress = $id('jira-progress');
  progress.style.display = 'none';
  progress.innerHTML = '';
  $id('jira-input-section').style.display = '';
  $id('modal-jira-import').disabled = false;
}

function openJiraEpicModal() {
  _resetJiraModal();
  $id('modal-jira-overlay').classList.remove('hidden');
  $id('jira-epic-key').focus();
}

function closeJiraEpicModal() {
  if (_jiraImportES) {
    _jiraImportES.close();
    _jiraImportES = null;
  }
  $id('modal-jira-overlay').classList.add('hidden');
  _resetJiraModal();
}

let _jiraJqlTestOk = false;
let _jiraJqlImportES = null;
let _jiraJqlViewTrackPlanId = null;

function _resetJiraJqlModal() {
  _jiraJqlViewTrackPlanId = null;
  $id('jira-jql-name').value = '';
  $id('jira-jql-query').value = '';
  const status = $id('jira-jql-test-status');
  status.textContent = '';
  status.className = 'jira-status';
  const preview = $id('jira-jql-preview');
  preview.style.display = 'none';
  preview.innerHTML = '';
  const progress = $id('jira-jql-progress');
  progress.style.display = 'none';
  progress.innerHTML = '';
  const importBtn = $id('modal-jira-jql-import');
  importBtn.textContent = 'Import ✦';
  importBtn.disabled = true;
  $id('modal-jira-jql-test').disabled = false;
  $id('modal-jira-jql-cancel').textContent = 'Cancel';
  _jiraJqlTestOk = false;
}

function openJiraJqlModal() {
  _resetJiraJqlModal();
  $id('modal-jira-jql-overlay').classList.remove('hidden');
  $id('jira-jql-name').focus();
}

function closeJiraJqlModal() {
  if (_jiraJqlImportES) {
    _jiraJqlImportES.close();
    _jiraJqlImportES = null;
  }
  $id('modal-jira-jql-overlay').classList.add('hidden');
  _resetJiraJqlModal();
}

async function testJiraJql() {
  const jql = $id('jira-jql-query').value.trim();
  if (!jql) return;
  const status = $id('jira-jql-test-status');
  const preview = $id('jira-jql-preview');
  status.textContent = 'Validating…';
  status.className = 'jira-status loading';
  preview.style.display = 'none';
  preview.innerHTML = '';
  $id('modal-jira-jql-test').disabled = true;
  $id('modal-jira-jql-import').disabled = true;
  _jiraJqlTestOk = false;
  try {
    const result = await api.validateJql(jql);
    if (!result) {
      status.textContent = '✗ Server error — check Jira settings';
      status.className = 'jira-status err';
    } else if (result.ok) {
      status.textContent = `✓ ${result.total} issue${result.total !== 1 ? 's' : ''} matched`;
      status.className = 'jira-status ok';
      if (result.preview && result.preview.length > 0) {
        preview.style.display = 'block';
        preview.innerHTML = result.preview
          .map(s => `<div class="jira-progress-item"><span class="jira-progress-summary" style="max-width:100%">${escapeHtml(s)}</span></div>`)
          .join('');
      }
      _jiraJqlTestOk = true;
      $id('modal-jira-jql-import').disabled = false;
    } else {
      status.textContent = `✗ ${result.error || 'Invalid JQL'}`;
      status.className = 'jira-status err';
    }
  } catch (err) {
    status.textContent = `✗ ${err.message || 'Connection error'}`;
    status.className = 'jira-status err';
  } finally {
    $id('modal-jira-jql-test').disabled = false;
  }
}

function importJiraJql() {
  if (_jiraJqlViewTrackPlanId) {
    closeJiraJqlModal();
    state.selectedPlanId = _jiraJqlViewTrackPlanId;
    refresh();
    return;
  }

  const name = $id('jira-jql-name').value.trim();
  const jql = $id('jira-jql-query').value.trim();
  if (!name) { $id('jira-jql-name').focus(); return; }
  if (!jql) { $id('jira-jql-query').focus(); return; }
  if (!_jiraJqlTestOk) {
    const status = $id('jira-jql-test-status');
    status.textContent = 'Please test the JQL query first.';
    status.className = 'jira-status err';
    return;
  }

  const status = $id('jira-jql-test-status');
  const importBtn = $id('modal-jira-jql-import');
  const testBtn = $id('modal-jira-jql-test');
  const preview = $id('jira-jql-preview');
  const progress = $id('jira-jql-progress');

  status.textContent = 'Starting import…';
  status.className = 'jira-status loading';
  importBtn.disabled = true;
  testBtn.disabled = true;
  preview.style.display = 'none';
  progress.style.display = 'block';
  progress.innerHTML = '';

  if (_jiraJqlImportES) { _jiraJqlImportES.close(); _jiraJqlImportES = null; }

  let completePlanId = null;
  let completeTaskCount = 0;
  const url = `/api/jira/jql-import/stream?jql=${encodeURIComponent(jql)}&track_name=${encodeURIComponent(name)}`;
  const es = new EventSource(url);
  _jiraJqlImportES = es;

  es.onmessage = (evt) => {
    const raw = evt.data;
    if (raw === '__DONE__') {
      es.close();
      _jiraJqlImportES = null;
      if (completePlanId) {
        const taskWord = completeTaskCount === 1 ? 'task' : 'tasks';
        status.textContent = `✓ ${completeTaskCount} ${taskWord} imported`;
        status.className = 'jira-status ok';
        _jiraJqlViewTrackPlanId = completePlanId;
        importBtn.textContent = 'View Track →';
        importBtn.disabled = false;
        $id('modal-jira-jql-cancel').textContent = 'Close';
      } else {
        testBtn.disabled = false;
      }
      return;
    }
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }
    switch (msg.event) {
      case 'error':
        status.textContent = `✗ ${msg.detail || 'Import failed'}`;
        status.className = 'jira-status err';
        importBtn.disabled = false;
        testBtn.disabled = false;
        es.close();
        _jiraJqlImportES = null;
        break;
      case 'start':
        status.textContent = `Refining ${msg.total} issue${msg.total !== 1 ? 's' : ''}…`;
        status.className = 'jira-status loading';
        break;
      case 'issue_start': {
        const row = document.createElement('div');
        row.className = 'jira-progress-item';
        row.id = `jql-issue-${msg.key}`;
        row.innerHTML = `<span class="jira-progress-icon">⋯</span><span class="jira-progress-key">${escapeHtml(msg.key)}</span><span class="jira-progress-summary">${escapeHtml(msg.summary)}</span>`;
        progress.appendChild(row);
        progress.scrollTop = progress.scrollHeight;
        break;
      }
      case 'issue_done': {
        const row = $id(`jql-issue-${msg.key}`);
        if (row) row.querySelector('.jira-progress-icon').textContent = '✓';
        break;
      }
      case 'issue_error': {
        const row = $id(`jql-issue-${msg.key}`);
        if (row) row.querySelector('.jira-progress-icon').textContent = '✗';
        break;
      }
      case 'complete':
        completePlanId = msg.plan_id;
        completeTaskCount = msg.task_count || 0;
        break;
    }
  };

  es.onerror = () => {
    es.close();
    _jiraJqlImportES = null;
    status.textContent = '✗ Connection lost during import';
    status.className = 'jira-status err';
    importBtn.disabled = false;
    testBtn.disabled = false;
  };
}

function importJiraEpic() {
  const epicKey = $id('jira-epic-key').value.trim().toUpperCase();
  if (!epicKey) return;

  const status = $id('jira-import-status');
  const importBtn = $id('modal-jira-import');
  const progress = $id('jira-progress');

  status.textContent = 'Connecting to Jira…';
  status.className = 'jira-status loading';
  importBtn.disabled = true;
  $id('jira-input-section').style.display = 'none';

  if (_jiraImportES) { _jiraImportES.close(); _jiraImportES = null; }

  const childItems = {};
  let completePlanId = null;

  const es = new EventSource(`/api/jira/import-epic/stream?epic_key=${encodeURIComponent(epicKey)}`);
  _jiraImportES = es;

  es.onmessage = (evt) => {
    const raw = evt.data;
    if (raw === '__DONE__') {
      es.close();
      _jiraImportES = null;
      if (completePlanId) {
        closeJiraEpicModal();
        state.selectedPlanId = completePlanId;
        refresh();
      }
      return;
    }
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }

    if (msg.event === 'error') {
      status.textContent = msg.detail || 'Import failed';
      status.className = 'jira-status err';
      $id('jira-input-section').style.display = '';
      importBtn.disabled = false;
      es.close();
      _jiraImportES = null;
      return;
    }
    if (msg.event === 'start') {
      const noun = msg.total === 1 ? 'issue' : 'issues';
      status.textContent = `${msg.summary} — ${msg.total} ${noun}`;
      status.className = 'jira-status ok';
      if (msg.total > 0) progress.style.display = 'block';
      return;
    }
    if (msg.event === 'child_start') {
      const item = document.createElement('div');
      item.className = 'jira-progress-item';
      item.innerHTML = `<span class="jira-progress-icon">⋯</span><span class="jira-progress-key">${msg.key}</span><span class="jira-progress-summary">${msg.summary}</span>`;
      progress.appendChild(item);
      childItems[msg.key] = item;
      progress.scrollTop = progress.scrollHeight;
      return;
    }
    if (msg.event === 'child_done') {
      const item = childItems[msg.key];
      if (item) { item.querySelector('.jira-progress-icon').textContent = '✓'; item.classList.add('done'); }
      return;
    }
    if (msg.event === 'child_error') {
      const item = childItems[msg.key];
      if (item) { item.querySelector('.jira-progress-icon').textContent = '✗'; item.classList.add('err'); }
      return;
    }
    if (msg.event === 'complete') {
      completePlanId = msg.plan_id;
      status.textContent = 'Import complete!';
      status.className = 'jira-status ok';
    }
  };

  es.onerror = () => {
    es.close();
    _jiraImportES = null;
    status.textContent = 'Connection error during import';
    status.className = 'jira-status err';
    $id('jira-input-section').style.display = '';
    importBtn.disabled = false;
  };
}

function _buildSpec(name, goal, context, requirements, constraints, outOfScope) {
  const parts = [`# Spec: ${name}\n`];
  if (goal)        parts.push(`## Goal\n\n${goal}\n`);
  if (context)     parts.push(`## Context\n\n${context}\n`);
  if (requirements) parts.push(`## Requirements\n\n${requirements.split('\n').map(l => l.trim() ? `- ${l.trim()}` : '').filter(Boolean).join('\n')}\n`);
  if (constraints) parts.push(`## Constraints\n\n${constraints}\n`);
  if (outOfScope)  parts.push(`## Out of Scope\n\n${outOfScope}\n`);
  parts.push('## Tasks\n\n_(To be generated by planner)_\n');
  return parts.join('\n');
}

async function createPlan(withGenerate = false) {
  const name = $id('modal-plan-name').value.trim();
  if (!name) return;
  const trackType = state.newTrackType;

  if (trackType === 'feature') {
    const goal         = $id('spec-goal').value.trim();
    const context      = $id('spec-context').value.trim();
    const requirements = $id('spec-requirements').value.trim();
    const constraints  = $id('spec-constraints').value.trim();
    const outOfScope   = $id('spec-out-of-scope').value.trim();
    const hasSpec = goal || requirements;

    closeModal();
    const plan = await api.createTrack(name, 'feature');
    if (!plan || !plan.id) { await refresh(); return; }

    if (hasSpec) {
      const spec = _buildSpec(name, goal, context, requirements, constraints, outOfScope);
      await api.saveSpec(plan.id, spec);
    }

    state.selectedPlanId = plan.id;
    await refresh();

    if (hasSpec) _switchTab('spec');

    if (withGenerate === 'phases') {
      generatePhases(plan.id);
    } else if (withGenerate) {
      if (hasSpec) refineAndGenerate(plan.id);
      else generateTasks(plan.id);
    }
  } else {
    // task or debug
    const descId = trackType === 'debug' ? 'debug-description' : 'task-description';
    const description = $id(descId).value.trim();
    const subtypes = [];
    if (trackType === 'task') {
      if ($id('task-subtype-test').checked) subtypes.push('test');
      if ($id('task-subtype-doc').checked) subtypes.push('doc');
    } else {
      if ($id('debug-subtype-regression').checked) subtypes.push('regression');
    }

    closeModal();
    const plan = await api.createTrack(name, trackType);
    if (!plan || !plan.id) { await refresh(); return; }

    state.selectedPlanId = plan.id;
    await refresh();

    if (withGenerate === 'phases') {
      generatePhases(plan.id);
    } else if (withGenerate && description) {
      await generateTasksFromTemplate(plan.id, trackType, description, subtypes);
    }
  }
}

async function generateTasksFromTemplate(planId, trackType, description, subtypes) {
  const result = await api.generateTemplate(planId, description, subtypes);
  if (!result) return;
  const titles = (result.tasks || []).map(t => `  • ${t.title}`).join('\n');
  showToast(`✓ ${result.count} tasks created`);
  await refresh();
  _switchTab('tasks');
}

function _switchTab(tabName) {
  document.querySelectorAll('.tab').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tabName);
  });
  document.querySelectorAll('.tab-pane').forEach(p => {
    p.classList.toggle('active', p.id === `tab-${tabName}`);
  });
  state.activeTab = tabName;
  if (state.selectedPlanId) {
    api.getTrack(state.selectedPlanId).then(plan => {
      if (plan) renderTabContent(plan, tabName);
    });
  }
}

function generateTasks(planId) {
  state.outputText = '';
  state.outputRunning = true;
  _openOutputTerminal(planId, '⚡ Gen tasks');
  _setOutputHeader('▶ Generating tasks…');

  _startStream(`/api/tracks/${planId}/tasks/generate`, {
    onMeta: (t) => { _setOutputHeader('▶ ' + t); },
    onText: _appendOutput,
    onDone: () => { state.outputRunning = false; refresh(); },
    onError: () => { state.outputRunning = false; _appendOutput('\n⚠ Connection error\n'); },
  });
}

/** Rewrite spec with LLM, then navigate to Spec tab. */
function refineSpec(planId) {
  state.outputText = '';
  state.outputRunning = true;
  _openOutputTerminal(planId, '⚡ Refine spec');
  _setOutputHeader('▶ Refining spec…');

  _startStream(`/api/tracks/${planId}/spec/refine`, {
    onMeta: (t) => { _setOutputHeader('▶ ' + t); },
    onText: _appendOutput,
    onDone: () => {
      state.outputRunning = false;
      _switchTab('spec');
    },
    onError: () => { state.outputRunning = false; _appendOutput('\n⚠ Connection error\n'); },
  });
}

/** Rewrite spec with LLM, then immediately generate tasks - single continuous output. */
function refineAndGenerate(planId) {
  state.outputText = '';
  state.outputRunning = true;
  _openOutputTerminal(planId, '⚡ Refine+Gen');
  _setOutputHeader('▶ Refining spec…');

  _startStream(`/api/tracks/${planId}/spec/refine`, {
    onMeta: (t) => { _setOutputHeader('▶ ' + t); },
    onText: _appendOutput,
    onDone: () => {
      _appendOutput('\n----------------------------------------\n');
      _setOutputHeader('▶ Generating tasks…');
      _startStream(`/api/tracks/${planId}/tasks/generate`, {
        onMeta: (t) => { _setOutputHeader('▶ ' + t); },
        onText: _appendOutput,
        onDone: () => { state.outputRunning = false; refresh(); },
        onError: () => { state.outputRunning = false; _appendOutput('\n⚠ Error during task generation\n'); },
      });
    },
    onError: () => { state.outputRunning = false; _appendOutput('\n⚠ Error during spec refinement\n'); },
  });
}

// -- Spec interview ----------------------------------------------------------
function openInterviewStart(planId) {
  _switchToOutputTab();
  state.outputText = '';
  state.outputRunning = false;
  _setOutputHeader('✦ Spec Interview', true);
  renderOutputPane();
  $id('interview-start').classList.remove('hidden');
  $id('interview-answer-panel').classList.add('hidden');
  $id('review-actions').classList.add('hidden');
  $id('interview-description').value = '';
  setTimeout(() => $id('interview-description').focus(), 50);
  state.interview = { planId, description: '', qa: [], currentQuestion: null };
}

function cancelInterviewStart() {
  $id('interview-start').classList.add('hidden');
  state.interview = null;
}

function startInterviewFromInput() {
  const description = $id('interview-description').value.trim();
  if (!description || !state.interview) return;
  state.interview.description = description;
  $id('interview-start').classList.add('hidden');
  _runInterviewTurn(state.interview.planId, description, []);
}

async function _runInterviewTurn(planId, description, qa) {
  const posBeforeTurn = state.outputText.length;
  state.outputRunning = true;
  renderOutputPane();

  await _startPostStream(`/api/tracks/${planId}/spec/interview`, { description, qa }, {
    onMeta: (t) => { _setOutputHeader('▶ ' + t, true); },
    onText: _appendOutput,
    onDone: () => { state.outputRunning = false; renderOutputPane(); },
    onError: () => { state.outputRunning = false; _appendOutput('\n⚠ Connection error'); renderOutputPane(); },
    onSignal: (sig) => {
      if (sig === '__QUESTION__') {
        const question = state.outputText.slice(posBeforeTurn).trim();
        if (state.interview) state.interview.currentQuestion = question;
        $id('interview-answer-panel').classList.remove('hidden');
        $id('interview-answer').value = '';
        setTimeout(() => $id('interview-answer').focus(), 50);
      } else if (sig === '__SPEC_COMPLETE__') {
        state.interview = null;
        $id('interview-answer-panel').classList.add('hidden');
        showToast('✓ Spec written!');
        refresh().then(() => _switchTab('spec'));
      }
    },
  });
}

async function submitInterviewAnswer() {
  if (!state.interview) return;
  const answer = $id('interview-answer').value.trim();
  if (!answer) { $id('interview-answer').focus(); return; }
  const q = state.interview.currentQuestion || '';
  state.interview.qa.push({ q, a: answer });
  $id('interview-answer-panel').classList.add('hidden');
  _appendOutput(`\n\n→ ${answer}\n\n`);
  await _runInterviewTurn(state.interview.planId, state.interview.description, state.interview.qa);
}

async function finishInterview() {
  if (!state.interview) return;
  const q = state.interview.currentQuestion || '';
  state.interview.qa.push({ q, a: 'I have no more to add. Please write the spec with the information provided.' });
  $id('interview-answer-panel').classList.add('hidden');
  _appendOutput('\n\n→ [Write spec with available information]\n\n');
  await _runInterviewTurn(state.interview.planId, state.interview.description, state.interview.qa);
}

// -- Code review -------------------------------------------------------------
function uiReviewTask() {
  const t = _getUiTask();
  if (t) reviewTask(state.selectedPlanId, t.id);
}

function reviewTask(planId, taskId) {
  state.outputText = '';
  state.outputRunning = true;
  state.reviewTask = { planId, taskId, verdict: null, issues: '' };
  _switchToOutputTab();
  _setOutputHeader('⊙ Reviewing…', true);
  $id('review-actions').classList.add('hidden');
  $id('interview-start').classList.add('hidden');
  $id('interview-answer-panel').classList.add('hidden');
  renderOutputPane();

  _startStream(`/api/tracks/${planId}/tasks/${taskId}/review`, {
    onMeta: (t) => { _setOutputHeader('⊙ ' + t, true); },
    onText: _appendOutput,
    onDone: () => { state.outputRunning = false; renderOutputPane(); },
    onError: () => { state.outputRunning = false; _appendOutput('\n⚠ Connection error'); renderOutputPane(); },
    onSignal: (sig) => {
      if (sig === '__REVIEW_PASS__') {
        if (state.reviewTask) state.reviewTask.verdict = 'PASS';
        showToast('✓ Review passed!');
      } else if (sig === '__REVIEW_FAIL__') {
        if (state.reviewTask) {
          state.reviewTask.verdict = 'FAIL';
          state.reviewTask.issues = state.outputText.trim();
        }
        $id('review-actions').classList.remove('hidden');
        showToast('✗ Review failed - create a rework task below');
      }
    },
  });
}

async function createReworkTask() {
  if (!state.reviewTask) return;
  const { planId, taskId, issues } = state.reviewTask;
  const task = await api.reworkTask(planId, taskId, issues);
  if (task && task.id) {
    $id('review-actions').classList.add('hidden');
    state.reviewTask = null;
    showToast('Rework task created');
    await renderPanelFor(planId);
    await refreshSidebar();
  }
}

// -- Add task modal -----------------------------------------------------------
function openAddTaskModal(trackId) {
  state.addTaskTrackId = trackId;
  $id('add-task-title').value = '';
  $id('add-task-files').value = '';

  // Populate phase selector if the current plan has phases
  const plan = (state._lastPlan && state._lastPlan.id === trackId) ? state._lastPlan : null;
  const phases = (plan && plan.phases) ? plan.phases.filter(ph => ph.name) : [];
  const phaseRow = $id('add-task-phase-row');
  const phaseSelect = $id('add-task-phase');
  if (phases.length > 0) {
    phaseSelect.innerHTML = phases.map(ph => `<option value="${ph.id}">${escHtml(ph.name)}</option>`).join('');
    phaseRow.classList.remove('hidden');
  } else {
    phaseRow.classList.add('hidden');
  }

  $id('modal-add-task-overlay').classList.remove('hidden');
  setTimeout(() => $id('add-task-title').focus(), 50);
}

function closeAddTaskModal() {
  $id('modal-add-task-overlay').classList.add('hidden');
  state.addTaskTrackId = null;
}

async function confirmAddTask() {
  const title = $id('add-task-title').value.trim();
  if (!title || !state.addTaskTrackId) return;
  const trackId = state.addTaskTrackId;
  const phaseRow = $id('add-task-phase-row');
  const phaseId = !phaseRow.classList.contains('hidden') ? $id('add-task-phase').value : '';
  const filesRaw = $id('add-task-files').value.trim();
  const files = filesRaw ? filesRaw.split('\n').map(l => l.trim()).filter(Boolean) : [];
  closeAddTaskModal();
  const task = await api.addTask(trackId, title, phaseId, files);
  if (task && task.id) {
    showToast(`✓ Task added: ${task.title}`);
  }
  await renderPanelFor(trackId);
}

// -- Track done ----------------------------------------------------------------
async function confirmDoneTrack(trackId) {
  if (!confirm('Mark this track as done?')) return;
  const track = await api.doneTrack(trackId);
  if (track) {
    showToast('✓ Track marked as done');
    await refresh();
  }
}

// -- Utils ------------------------------------------------------------------
function stripAnsi(str) {
  return str.replace(/\x1b\[[0-9;]*[mGKHF]/g, '').replace(/\r/g, '');
}

function showToast(msg, duration = 3500) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.classList.add('toast-in'), 10);
  setTimeout(() => {
    el.classList.remove('toast-in');
    setTimeout(() => el.remove(), 300);
  }, duration);
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// -- Resizable console ------------------------------------------------------
function setupResizableConsole() {
  const handle = $id('console-resize-handle');
  const wrapper = $id('console-wrapper');
  if (!handle || !wrapper) return;

  let dragging = false;
  let startY = 0;
  let startH = 0;

  handle.addEventListener('mousedown', (e) => {
    if (state.consoleCollapsed) return;
    dragging = true;
    startY = e.clientY;
    startH = wrapper.getBoundingClientRect().height;
    handle.classList.add('dragging');
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const delta = startY - e.clientY;  // drag up = taller
    const minH = 80;
    const maxH = Math.floor(window.innerHeight * 0.75);
    const newH = Math.max(minH, Math.min(maxH, startH + delta));
    // 5px handle + bar-h embedded; store just the terminal area height in --console-h
    const barH = 34; // matches --console-bar-h
    document.documentElement.style.setProperty('--console-h', `${newH - barH - 5}px`);
    wrapper.style.height = `${newH}px`;
    _fitActive();
  });

  document.addEventListener('mouseup', () => {
    if (dragging) {
      dragging = false;
      handle.classList.remove('dragging');
      document.body.style.userSelect = '';
      _fitActive();
    }
  });
}

// -- Themes -----------------------------------------------------------------
const THEMES = {
  dark: {
    label: 'Dark',
    swatch: '#141414',
    css: {
      '--bg': '#0d0d0d', '--bg2': '#141414', '--bg3': '#1a1a1a',
      '--border': '#2a2a2a', '--text': '#e0e0e0', '--text-dim': '#666',
      '--text-muted': '#999', '--green': '#3fb950', '--yellow': '#d29922',
      '--red': '#f85149', '--blue': '#58a6ff', '--cyan': '#39c5cf',
      '--purple': '#bc8cff', '--accent': '#7c6af7', '--accent-hover': '#6a5acd',
    },
    term: { background: '#0d0d0d', foreground: '#e0e0e0', cursor: '#39c5cf', selection: '#2a4a5a' },
  },
  light: {
    label: 'Light',
    swatch: '#f5f5f0',
    css: {
      '--bg': '#f5f5f0', '--bg2': '#ececea', '--bg3': '#e3e3e0',
      '--border': '#d0d0cc', '--text': '#1a1a1a', '--text-dim': '#888',
      '--text-muted': '#555', '--green': '#1a7f37', '--yellow': '#9a6700',
      '--red': '#cf222e', '--blue': '#0550ae', '--cyan': '#1b7c83',
      '--purple': '#7a3e9d', '--accent': '#6f42c1', '--accent-hover': '#5a32a8',
    },
    term: { background: '#f5f5f0', foreground: '#1a1a1a', cursor: '#1b7c83', selection: '#c8e1e4' },
  },
  pastelOrange: {
    label: 'Pastel Orange',
    swatch: '#2e2a26',
    css: {
      '--bg': '#1e1b18', '--bg2': '#26221e', '--bg3': '#2e2a24',
      '--border': '#3d3830', '--text': '#e8e0d4', '--text-dim': '#6e6358',
      '--text-muted': '#a89880', '--green': '#6ab06a', '--yellow': '#e0945a',
      '--red': '#e06a5a', '--blue': '#7aaedd', '--cyan': '#7ac4c0',
      '--purple': '#c4a0e0', '--accent': '#d4a06a', '--accent-hover': '#b88a52',
    },
    term: { background: '#1e1b18', foreground: '#e8e0d4', cursor: '#e0945a', selection: '#3d3020' },
  },
  pastelViolet: {
    label: 'Pastel Violet',
    swatch: '#221e2e',
    css: {
      '--bg': '#181620', '--bg2': '#201e2c', '--bg3': '#282638',
      '--border': '#363250', '--text': '#dcd8ec', '--text-dim': '#6a6480',
      '--text-muted': '#9a94b8', '--green': '#7acc88', '--yellow': '#d4b06a',
      '--red': '#e07a88', '--blue': '#7aaae0', '--cyan': '#7ac4d4',
      '--purple': '#c0a0f0', '--accent': '#b8a0e8', '--accent-hover': '#9a88c8',
    },
    term: { background: '#181620', foreground: '#dcd8ec', cursor: '#c0a0f0', selection: '#362850' },
  },
  nord: {
    label: 'Nord',
    swatch: '#2e3440',
    css: {
      '--bg': '#242933', '--bg2': '#2e3440', '--bg3': '#363d4a',
      '--border': '#434c5e', '--text': '#eceff4', '--text-dim': '#616e88',
      '--text-muted': '#9099a8', '--green': '#a3be8c', '--yellow': '#ebcb8b',
      '--red': '#bf616a', '--blue': '#81a1c1', '--cyan': '#88c0d0',
      '--purple': '#b48ead', '--accent': '#88c0d0', '--accent-hover': '#78b0c0',
    },
    term: { background: '#242933', foreground: '#eceff4', cursor: '#88c0d0', selection: '#434c5e' },
  },
  solarized: {
    label: 'Solarized',
    swatch: '#002b36',
    css: {
      '--bg': '#002b36', '--bg2': '#073642', '--bg3': '#0d4050',
      '--border': '#1a5060', '--text': '#e0ddd0', '--text-dim': '#4a6070',
      '--text-muted': '#6a8090', '--green': '#859900', '--yellow': '#b58900',
      '--red': '#dc322f', '--blue': '#268bd2', '--cyan': '#2aa198',
      '--purple': '#6c71c4', '--accent': '#268bd2', '--accent-hover': '#1a75a8',
    },
    term: { background: '#002b36', foreground: '#e0ddd0', cursor: '#2aa198', selection: '#1a4050' },
  },
};

let _themeProjectKey = 'arche-theme-default';

function _themeKey() { return _themeProjectKey; }

// Apply theme visually (CSS + xterm + modal indicator) without persisting.
function _applyThemeCss(themeId) {
  const theme = THEMES[themeId] || THEMES.dark;
  const root = document.documentElement;
  Object.entries(theme.css).forEach(([k, v]) => root.style.setProperty(k, v));
  Object.assign(TERM_OPTS.theme, theme.term);
  state.terminals.forEach(({ term }) => {
    try { term.options.theme = { ...theme.term }; } catch (_) {}
  });
  document.querySelectorAll('.theme-option').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.themeId === themeId);
  });
}

// Apply theme and persist (localStorage + server). Called only on explicit user choice.
function applyTheme(themeId) {
  _applyThemeCss(themeId);
  localStorage.setItem(_themeKey(), themeId);
  apiFetch('/api/settings/theme', { method: 'POST', body: JSON.stringify({ theme: themeId }) }).catch(() => {});
}

function _buildThemeModal() {
  const list = $id('theme-options-list');
  list.innerHTML = Object.entries(THEMES).map(([id, t]) => `
    <button class="theme-option" data-theme-id="${id}" onclick="applyTheme('${id}');closeThemeModal()">
      <span class="theme-swatch" style="background:${t.swatch}"></span>${t.label}
    </button>`).join('');
}

function openThemeModal() {
  // Update active indicator
  document.querySelectorAll('.theme-option').forEach(btn => {
    const saved = localStorage.getItem(_themeKey()) || 'dark';
    btn.classList.toggle('active', btn.dataset.themeId === saved);
  });
  $id('modal-theme-overlay').classList.remove('hidden');
}

function closeThemeModal() {
  $id('modal-theme-overlay').classList.add('hidden');
}

// -- Settings modal -----------------------------------------------------------
let _settingsActiveTab = 'paths';
let _settingsModelsData = null;

function _switchSettingsTab(tab) {
  _settingsActiveTab = tab;
  document.querySelectorAll('.settings-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });
  $id('settings-tab-paths').classList.toggle('hidden', tab !== 'paths');
  $id('settings-tab-models').classList.toggle('hidden', tab !== 'models');
  $id('settings-tab-security').classList.toggle('hidden', tab !== 'security');
  $id('settings-tab-jira').classList.toggle('hidden', tab !== 'jira');
}

async function _loadModelsTab() {
  // Load tools inventory (all tools with availability flag)
  let toolsData = null;
  try { toolsData = await apiFetch('/api/config/tools'); } catch (_) {}
  const toolsTable = $id('settings-tools-table');
  toolsTable.innerHTML = '';
  for (const [alias, info] of Object.entries((toolsData || {}).tools || {})) {
    const chip = document.createElement('div');
    chip.className = 'settings-tool-chip' + (info.available ? ' available' : '');
    chip.title = info.description || alias;
    chip.innerHTML = `<span class="settings-tool-chip-dot"></span>${alias}`;
    toolsTable.appendChild(chip);
  }

  // Load phase→model config
  try {
    _settingsModelsData = await apiFetch('/api/settings/models');
  } catch (_) {
    _settingsModelsData = null;
  }
  const container = $id('settings-models-rows');
  container.innerHTML = '';
  if (!_settingsModelsData || !Object.keys(_settingsModelsData.tools || {}).length) {
    $id('settings-models-unavailable').classList.remove('hidden');
    return;
  }
  $id('settings-models-unavailable').classList.add('hidden');

  const { tools, current, phases, defaults } = _settingsModelsData;
  const currentAgents = _settingsModelsData.agents || {};
  const toolAliases = Object.keys(tools);

  // Fetch agents list for agent selects
  let agentsList = [];
  try {
    const agentsResp = await api.listAgents();
    agentsList = (agentsResp && agentsResp.agents) ? agentsResp.agents : [];
  } catch (_) {}

  // Header row (4 columns)
  ['Phase', 'Tool', 'Model', 'Agent'].forEach(h => {
    const hdr = document.createElement('div');
    hdr.className = 'settings-grid-header';
    hdr.textContent = h;
    container.appendChild(hdr);
  });

  for (const phase of (phases || [])) {
    const currentVal = current[phase] || defaults[phase] || '';
    let currentTool = toolAliases[0] || '';
    let currentModel = '';
    if (currentVal.includes('/')) {
      [currentTool, currentModel] = currentVal.split('/');
    }
    const currentAgentId = currentAgents[phase] || '';

    // Phase label
    const label = document.createElement('div');
    label.className = 'settings-phase-label';
    label.textContent = phase;

    // Tool select
    const toolSel = document.createElement('select');
    toolSel.id = `settings-tool-${phase}`;
    for (const toolAlias of toolAliases) {
      const opt = document.createElement('option');
      opt.value = toolAlias;
      opt.textContent = toolAlias;
      opt.title = tools[toolAlias]?.description || toolAlias;
      if (toolAlias === currentTool) opt.selected = true;
      toolSel.appendChild(opt);
    }

    // Model select - cascades from tool select
    const modelSel = document.createElement('select');
    modelSel.id = `settings-model-${phase}`;

    const populateModels = (toolAlias, selectedModel) => {
      modelSel.innerHTML = '';
      for (const [mAlias, mDesc] of Object.entries(tools[toolAlias]?.models || {})) {
        const opt = document.createElement('option');
        opt.value = mAlias;
        opt.textContent = `${mAlias} - ${mDesc}`;
        if (mAlias === selectedModel) opt.selected = true;
        modelSel.appendChild(opt);
      }
    };
    populateModels(currentTool || toolAliases[0], currentModel);
    toolSel.addEventListener('change', () => populateModels(toolSel.value, ''));

    // Agent select
    const agentSel = document.createElement('select');
    agentSel.id = `settings-agent-${phase}`;
    const noneOpt = document.createElement('option');
    noneOpt.value = '';
    noneOpt.textContent = '— none —';
    agentSel.appendChild(noneOpt);
    for (const a of agentsList) {
      const opt = document.createElement('option');
      opt.value = a.id;
      opt.textContent = a.name + (a.role ? ` (${a.role})` : '');
      if (a.id === currentAgentId) opt.selected = true;
      agentSel.appendChild(opt);
    }

    container.appendChild(label);
    container.appendChild(toolSel);
    container.appendChild(modelSel);
    container.appendChild(agentSel);
  }
}

async function _testJiraConnection(url, login, apiKey) {
  const status = $id('jira-connection-status');
  status.className = 'jira-status loading';
  status.textContent = 'Checking…';
  try {
    const result = await apiFetch('/api/settings/jira/validate', {
      method: 'POST',
      body: JSON.stringify({ url, login, api_key: apiKey }),
    });
    if (result.ok) {
      status.className = 'jira-status ok';
      status.textContent = `✓ Connected${result.display_name ? ` as ${result.display_name}` : ''}`;
    } else {
      status.className = 'jira-status err';
      status.textContent = `✗ ${result.error || 'Connection failed'}`;
    }
  } catch (err) {
    status.className = 'jira-status err';
    status.textContent = `✗ ${err.message || 'Request failed'}`;
  }
}

async function _loadJiraTab() {
  try {
    const data = await apiFetch('/api/settings/jira');
    $id('settings-jira-url').value = data.url || '';
    $id('settings-jira-login').value = data.login || '';
    $id('settings-jira-api-key').value = data.api_key || '';
  } catch (_) {}
  const toggle = $id('settings-jira-api-key-toggle');
  if (toggle && !toggle._jiraToggleBound) {
    toggle._jiraToggleBound = true;
    toggle.addEventListener('click', () => {
      const input = $id('settings-jira-api-key');
      input.type = input.type === 'password' ? 'text' : 'password';
    });
  }
  const testBtn = $id('settings-jira-test');
  if (testBtn && !testBtn._jiraTestBound) {
    testBtn._jiraTestBound = true;
    testBtn.addEventListener('click', () => {
      _testJiraConnection(
        $id('settings-jira-url').value.trim(),
        $id('settings-jira-login').value.trim(),
        $id('settings-jira-api-key').value
      );
    });
  }
}

async function openSettingsModal() {
  try {
    const data = await apiFetch('/api/settings/protected-paths');
    $id('settings-protected-paths').value = (data.protected_paths || []).join('\n');
  } catch (_) {}
  try {
    const pwStatus = await api.getPasswordStatus();
    if (pwStatus && pwStatus.has_password) {
      $id('settings-password-input').placeholder = 'Leave empty to keep current password';
    } else {
      $id('settings-password-input').placeholder = 'Enter password (min 4 chars)';
    }
  } catch (_) {}
  await _loadJiraTab();
  _switchSettingsTab('paths');
  await _loadModelsTab();
  $id('modal-settings-overlay').classList.remove('hidden');
}

function closeSettingsModal() {
  $id('modal-settings-overlay').classList.add('hidden');
}

async function saveSettings() {
  try {
    if (_settingsActiveTab === 'paths') {
      const raw = $id('settings-protected-paths').value;
      const paths = raw.split('\n').map(l => l.trim()).filter(Boolean);
      await apiFetch('/api/settings/protected-paths', {
        method: 'POST',
        body: JSON.stringify({ protected_paths: paths }),
      });
    } else if (_settingsActiveTab === 'models' && _settingsModelsData) {
      const models = {};
      for (const phase of (_settingsModelsData.phases || [])) {
        const toolSel = $id(`settings-tool-${phase}`);
        const modelSel = $id(`settings-model-${phase}`);
        if (toolSel && modelSel) models[phase] = `${toolSel.value}/${modelSel.value}`;
      }
      const agents = {};
      for (const phase of (_settingsModelsData.phases || [])) {
        const asel = $id(`settings-agent-${phase}`);
        if (asel && asel.value) agents[phase] = asel.value;
      }
      await apiFetch('/api/settings/models', {
        method: 'PATCH',
        body: JSON.stringify({ models, agents }),
      });
    } else if (_settingsActiveTab === 'security') {
      const password = $id('settings-password-input').value;
      if (password) {
        await updateSessionPassword(password);
      }
    } else if (_settingsActiveTab === 'jira') {
      const jiraUrl = $id('settings-jira-url').value.trim();
      const jiraLogin = $id('settings-jira-login').value.trim();
      const jiraApiKey = $id('settings-jira-api-key').value;
      await apiFetch('/api/settings/jira', {
        method: 'PATCH',
        body: JSON.stringify({ url: jiraUrl, login: jiraLogin, api_key: jiraApiKey }),
      });
      showToast('Settings saved');
      _testJiraConnection(jiraUrl, jiraLogin, jiraApiKey);
      updateJiraButtonState();
      return;
    }
    closeSettingsModal();
    showToast('Settings saved');
  } catch (err) {
    showToast(`Save failed: ${err.message || err}`);
  }
}

function _initThemeListeners() {
  _buildThemeModal();
  // Apply a quick visual default without saving - the authoritative theme comes from the server in init().
  const earlyKey = Object.keys(localStorage).find(k => k.startsWith('arche-theme-'));
  const earlyTheme = earlyKey ? localStorage.getItem(earlyKey) : null;
  _applyThemeCss(earlyTheme && THEMES[earlyTheme] ? earlyTheme : 'dark');

  $id('theme-close').addEventListener('click', closeThemeModal);
  $id('modal-theme-overlay').addEventListener('click', (e) => {
    if (e.target === $id('modal-theme-overlay')) closeThemeModal();
  });
}

function setupTheme(projectName) {
  _themeProjectKey = `arche-theme-${projectName || 'default'}`;
  const saved = localStorage.getItem(_themeKey());
  if (saved && THEMES[saved]) _applyThemeCss(saved);
}

// -- Password Lock -----------------------------------------------------------
async function setupLockScreen() {
  // Check if password is set
  const status = await api.getPasswordStatus();
  if (!status) return;

  state.hasPassword = status.has_password;

  // Check localStorage for unlock status (shared across tabs, private browsing friendly)
  // Default: if password exists, assume locked unless explicitly marked as unlocked
  const isUnlockedSession = localStorage.getItem('isLocked') === 'false';

  if (state.hasPassword && !isUnlockedSession) {
    state.sessionLocked = true;
    openLockScreenModal();
  }

  updateLockButtonEmoji();
}

function updateLockButtonEmoji() {
  const btn = $id('btn-lock');
  if (!btn) return;
  btn.textContent = state.sessionLocked ? '🔒' : '🔓';
}

function setupLockStorageSync() {
  // Sync lock state across tabs when localStorage changes
  window.addEventListener('storage', (event) => {
    if (event.key === 'isLocked') {
      const isNowLocked = event.newValue === 'true';

      if (isNowLocked && state.hasPassword && !state.sessionLocked) {
        // Lock was activated in another tab - lock this tab too
        state.sessionLocked = true;
        openLockScreenModal();
        updateLockButtonEmoji();
      } else if (!isNowLocked && state.sessionLocked) {
        // Lock was deactivated in another tab - unlock this tab too
        state.sessionLocked = false;
        closeLockScreenModal();
        updateLockButtonEmoji();
      }
    }
  });
}

function openLockSetupModal() {
  $id('lock-setup-password-input').value = '';
  $id('lock-setup-password-input').type = 'password';
  $id('lock-setup-password-toggle').textContent = '👁';
  $id('modal-lock-setup-overlay').classList.remove('hidden');
  $id('lock-setup-password-input').focus();
}

function closeLockSetupModal() {
  $id('modal-lock-setup-overlay').classList.add('hidden');
}

function openLockScreenModal() {
  $id('lock-screen-password-input').value = '';
  $id('lock-screen-password-input').type = 'password';
  $id('lock-screen-password-toggle').textContent = '👁';
  $id('lock-screen-error').classList.add('hidden');
  $id('modal-lock-screen-overlay').classList.remove('hidden');
  $id('lock-screen-password-input').focus();
}

function closeLockScreenModal() {
  $id('modal-lock-screen-overlay').classList.add('hidden');
}

async function toggleLockSession() {
  // Close settings dropdown
  $id('settings-dropdown').classList.add('hidden');

  if (!state.hasPassword) {
    // First time - open setup modal
    openLockSetupModal();
  } else {
    // Already has password - lock the session
    state.sessionLocked = true;
    localStorage.setItem('isLocked', 'true');
    openLockScreenModal();
  }
}

async function saveLockPassword(password) {
  if (!password || password.length < 4) {
    alert('Password must be at least 4 characters');
    return false;
  }

  try {
    const result = await api.setupPassword(password);
    if (result && result.ok) {
      state.hasPassword = true;
      state.sessionLocked = true;
      localStorage.setItem('isLocked', 'true');
      closeLockSetupModal();
      updateLockButtonEmoji();
      showToast('Password set and session locked');
      return true;
    }
  } catch (e) {
    console.error('Failed to set password', e);
  }
  return false;
}

async function verifyPasswordAndUnlock(password) {
  try {
    const result = await api.verifyPassword(password);
    if (result && result.ok) {
      state.sessionLocked = false;
      localStorage.setItem('isLocked', 'false');
      closeLockScreenModal();
      updateLockButtonEmoji();
      showToast('Session unlocked');
      return true;
    } else {
      $id('lock-screen-error').classList.remove('hidden');
      $id('lock-screen-password-input').value = '';
      return false;
    }
  } catch (e) {
    console.error('Failed to verify password', e);
    $id('lock-screen-error').classList.remove('hidden');
    return false;
  }
}

async function updateSessionPassword(password) {
  if (!password || password.length < 4) {
    alert('Password must be at least 4 characters');
    return false;
  }

  try {
    const result = await api.updatePassword(password);
    if (result && result.ok) {
      state.hasPassword = true;
      $id('settings-password-input').value = '';
      showToast('Password updated');
      return true;
    }
  } catch (e) {
    console.error('Failed to update password', e);
  }
  return false;
}

// -- Boot -------------------------------------------------------------------
window.addEventListener('DOMContentLoaded', init);
window.applyTheme = applyTheme;
window.closeThemeModal = closeThemeModal;

// Expose for inline handlers
window.markTaskDone = markTaskDone;
window.markTaskBlocked = markTaskBlocked;
window.switchToPlan = switchToPlan;
window.toggleSession = toggleSession;
window.runTask = runTask;
window.runBulkTasks = runBulkTasks;
window.switchCurrentTask = switchCurrentTask;
window.openEditTask = openEditTask;
window.openDoneModal = openDoneModal;
window.selectTerminal = selectTerminal;
window.removeTerminal = removeTerminal;
window.addTerminal = addTerminal;
window.uiRunTask = uiRunTask;
window.uiSelectTask = uiSelectTask;
window.uiEditTask = uiEditTask;
window.uiDoneTask = uiDoneTask;
window.uiBlockTask = uiBlockTask;
window.uiBulkRunTasks = uiBulkRunTasks;
window.openBlockModal = openBlockModal;
window.closeBlockModal = closeBlockModal;
window.confirmBlockTask = confirmBlockTask;
window.selectAllTasks = selectAllTasks;
window.clearBulkSelection = clearBulkSelection;
window.generateTasks = generateTasks;
window.refineSpec = refineSpec;
window.openSpecEditor = openSpecEditor;
window.saveSpecEdit = saveSpecEdit;
window.cancelSpecEdit = cancelSpecEdit;
window.refineAndGenerate = refineAndGenerate;
window.generatePhases = generatePhases;
window.generateTasksForPhase = generateTasksForPhase;
window.uiDeleteTask = uiDeleteTask;
window.uiDeletePhase = uiDeletePhase;
window.openNewPhaseModal = openNewPhaseModal;
window.closePhaseModal = closePhaseModal;
window.confirmNewPhase = confirmNewPhase;
window.openInterviewStart = openInterviewStart;
window.cancelInterviewStart = cancelInterviewStart;
window.startInterviewFromInput = startInterviewFromInput;
window.submitInterviewAnswer = submitInterviewAnswer;
window.finishInterview = finishInterview;
window.uiReviewTask = uiReviewTask;
window.reviewTask = reviewTask;
window.createReworkTask = createReworkTask;
window.openRunModal = openRunModal;
window.closeRunModal = closeRunModal;
window.confirmRunTask = confirmRunTask;
window.openAddTaskModal = openAddTaskModal;
window.closeAddTaskModal = closeAddTaskModal;
window.confirmAddTask = confirmAddTask;
window.openTrackFilesModal = openTrackFilesModal;
window.toggleLockSession = toggleLockSession;
window.closeLockSetupModal = closeLockSetupModal;
window.closeLockScreenModal = closeLockScreenModal;
window.confirmDoneTrack = confirmDoneTrack;
