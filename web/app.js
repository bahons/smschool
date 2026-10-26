// Smart School AI - Web Interface Controller

let selectedFile = null;

// DOM Elements
const dropzone = document.getElementById('dropzone');
const videoFileInput = document.getElementById('videoFileInput');
const selectedFileInfo = document.getElementById('selectedFileInfo');
const selectedFileName = document.getElementById('selectedFileName');
const clearFileBtn = document.getElementById('clearFileBtn');
const blurHeadCheck = document.getElementById('blurHeadCheck');
const startAnalyzeBtn = document.getElementById('startAnalyzeBtn');
const progressContainer = document.getElementById('progressContainer');
const progressText = document.getElementById('progressText');

const resultsSection = document.getElementById('resultsSection');
const statusBanner = document.getElementById('statusBanner');
const statusIcon = document.getElementById('statusIcon');
const statusTitle = document.getElementById('statusTitle');
const statusDesc = document.getElementById('statusDesc');

const valState = document.getElementById('valState');
const valAlerts = document.getElementById('valAlerts');
const valAlertTime = document.getElementById('valAlertTime');
const valPeakIndex = document.getElementById('valPeakIndex');
const valFps = document.getElementById('valFps');
const valLatency = document.getElementById('valLatency');

const annotatedVideoPlayer = document.getElementById('annotatedVideoPlayer');
const timelineImg = document.getElementById('timelineImg');
const alertPhotoBox = document.getElementById('alertPhotoBox');
const alertScreenshotImg = document.getElementById('alertScreenshotImg');

const loadDemoCalm = document.getElementById('loadDemoCalm');
const loadDemoFight = document.getElementById('loadDemoFight');
const loadComparison = document.getElementById('loadComparison');
const comparisonSection = document.getElementById('comparisonSection');

// Drag and drop events
dropzone.addEventListener('click', () => videoFileInput.click());

dropzone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', () => {
  dropzone.classList.remove('dragover');
});

dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  if (e.dataTransfer.files.length > 0) {
    handleFileSelected(e.dataTransfer.files[0]);
  }
});

videoFileInput.addEventListener('change', (e) => {
  if (e.target.files.length > 0) {
    handleFileSelected(e.target.files[0]);
  }
});

function handleFileSelected(file) {
  selectedFile = file;
  selectedFileName.textContent = file.name + ` (${(file.size / (1024 * 1024)).toFixed(1)} MB)`;
  selectedFileInfo.style.display = 'flex';
  startAnalyzeBtn.disabled = false;
  dropzone.style.display = 'none';
}

clearFileBtn.addEventListener('click', () => {
  selectedFile = null;
  videoFileInput.value = '';
  selectedFileInfo.style.display = 'none';
  dropzone.style.display = 'block';
  startAnalyzeBtn.disabled = true;
});

// Upload and analyze
startAnalyzeBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  startAnalyzeBtn.disabled = true;
  progressContainer.style.display = 'flex';
  progressText.textContent = 'Видео серверге жүктелуде және өңделуде... (10-25 сек)';
  resultsSection.style.display = 'none';
  comparisonSection.style.display = 'none';

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('blur_head', blurHeadCheck.checked);

  try {
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Сервер қатесі орын алды');
    }

    const data = await response.json();
    renderResults(data);
  } catch (error) {
    alert('Қате орын алды: ' + error.message);
  } finally {
    progressContainer.style.display = 'none';
    startAnalyzeBtn.disabled = false;
  }
});

function renderResults(data) {
  const summary = data.summary;
  const isAlert = summary.alert_triggered;

  // Status Banner
  if (isAlert) {
    statusBanner.className = 'status-banner danger';
    statusIcon.textContent = '🚨';
    statusTitle.textContent = 'ҚАУІП: ТӨБЕЛЕС АНЫҚТАЛДЫ!';
    statusDesc.textContent = `2 секунд үздіксіз шектен асу тіркелді. Алғашқы дабыл сәті: ${summary.first_alert_time_sec ? summary.first_alert_time_sec.toFixed(2) + 'с' : '—'}`;
    valState.textContent = 'ҚАУІП';
    valState.style.color = '#ef4444';
  } else {
    statusBanner.className = 'status-banner';
    statusIcon.textContent = '🟢';
    statusTitle.textContent = 'НОРМА: Сынып тыныш күйде';
    statusDesc.textContent = 'Агрессивті білек қимылдары немесе конфликттік қауіп байқалмады.';
    valState.textContent = 'НОРМА';
    valState.style.color = '#22c55e';
  }

  // Metrics
  valAlerts.textContent = summary.total_alerts || 0;
  valAlertTime.textContent = summary.first_alert_time_sec ? `${summary.first_alert_time_sec.toFixed(2)} сек` : 'Жоқ';
  valPeakIndex.textContent = summary.peak_conflict_index ? summary.peak_conflict_index.toFixed(2) : '0.00';
  valFps.textContent = `${summary.avg_processing_fps || 0} FPS`;
  valLatency.textContent = `${Math.round(summary.avg_latency_ms || 0)} ms`;

  // Media
  annotatedVideoPlayer.src = data.video_url + '?t=' + new Date().getTime();
  annotatedVideoPlayer.load();

  timelineImg.src = data.timeline_url + '?t=' + new Date().getTime();

  if (data.alert_screenshot_url) {
    alertPhotoBox.style.display = 'block';
    alertScreenshotImg.src = data.alert_screenshot_url + '?t=' + new Date().getTime();
  } else {
    alertPhotoBox.style.display = 'none';
  }

  resultsSection.style.display = 'block';
  resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Load precomputed demos
loadDemoCalm.addEventListener('click', () => {
  renderResults({
    video_url: '/outputs/video2_calm/annotated.mp4',
    timeline_url: '/outputs/video2_calm/conflict_timeline.png',
    alert_screenshot_url: null,
    summary: {
      alert_triggered: false,
      first_alert_time_sec: null,
      total_alerts: 0,
      peak_conflict_index: 0.57,
      avg_processing_fps: 12.3,
      avg_latency_ms: 60
    }
  });
});

loadDemoFight.addEventListener('click', () => {
  renderResults({
    video_url: '/outputs/video1_fight/annotated.mp4',
    timeline_url: '/outputs/video1_fight/conflict_timeline.png',
    alert_screenshot_url: '/outputs/video1_fight/alert_screenshot.png',
    summary: {
      alert_triggered: true,
      first_alert_time_sec: 2.37,
      total_alerts: 1,
      peak_conflict_index: 0.85,
      avg_processing_fps: 14.0,
      avg_latency_ms: 54
    }
  });
});

loadComparison.addEventListener('click', () => {
  resultsSection.style.display = 'none';
  comparisonSection.style.display = 'block';
  comparisonSection.scrollIntoView({ behavior: 'smooth' });
});
