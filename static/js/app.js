// ==========================================
// EMAIL SENDING FUNCTIONALITY
// ==========================================

const emailForm = document.getElementById('emailForm');
const submitBtn = document.getElementById('submitBtn');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const downloadBtn = document.getElementById('downloadBtn');

if (emailForm) {
  emailForm.addEventListener('submit', handleEmailSubmit);
}

/**
 * Handle email form submission
 */
async function handleEmailSubmit(e) {
  e.preventDefault();

  // Update UI
  submitBtn.disabled = true;
  submitBtn.textContent = '⏳ Đang xử lý...';
  progressSection.style.display = 'block';
  downloadBtn.style.display = 'none';

  // Scroll to progress section on mobile
  if (window.innerWidth < 768) {
    setTimeout(() => {
      progressSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  }

  const formData = new FormData(emailForm);

  try {
    const response = await fetch('/send_emails', {
      method: 'POST',
      body: formData
    });

    const result = await response.json();

    if (result.error) {
      showError('❌ Lỗi: ' + result.error);
      resetForm();
      return;
    }

    const jobId = result.job_id;
    await pollEmailStatus(jobId);

  } catch (error) {
    showError('❌ Lỗi: ' + error.message);
    resetForm();
  }
}

/**
 * Poll email sending status
 */
async function pollEmailStatus(jobId) {
  return new Promise((resolve) => {
    const checkInterval = setInterval(async () => {
      try {
        const statusResponse = await fetch(`/check_status/${jobId}`);
        const status = await statusResponse.json();

        if (status.status === 'processing') {
          updateProgress(status);
        } else if (status.status === 'completed') {
          clearInterval(checkInterval);
          completeEmailSending(jobId);
          resolve();
        } else if (status.status === 'failed') {
          clearInterval(checkInterval);
          showError('❌ Gửi email thất bại!');
          resetForm();
          resolve();
        }
      } catch (error) {
        console.error('Error checking status:', error);
      }
    }, 2000);
  });
}

/**
 * Update progress bar
 */
function updateProgress(status) {
  const progress = status.total > 0 ? Math.round((status.progress / status.total) * 100) : 0;
  progressFill.style.width = progress + '%';
  progressFill.textContent = progress + '%';
  progressText.textContent = `Đã gửi ${status.progress}/${status.total} email...`;
}

/**
 * Complete email sending
 */
function completeEmailSending(jobId) {
  progressFill.style.width = '100%';
  progressFill.textContent = '100%';
  progressText.textContent = '✅ Hoàn tất! Nhấn nút bên dưới để tải file log.';

  downloadBtn.style.display = 'block';
  downloadBtn.onclick = () => {
    window.location.href = `/download_log/${jobId}`;
  };

  resetForm();
}

/**
 * Reset form state
 */
function resetForm() {
  submitBtn.disabled = false;
  submitBtn.textContent = '🚀 Gửi Email Tự Động';
}

/**
 * Show error notification
 */
function showError(message) {
  alert(message);
  progressSection.style.display = 'none';
}

// ==========================================
// SPLIT FILE FUNCTIONALITY
// ==========================================

const splitForm = document.getElementById('splitForm');
const splitProgressSection = document.getElementById('splitProgressSection');

if (splitForm) {
  splitForm.addEventListener('submit', handleSplitSubmit);
}

/**
 * Handle split file form submission
 */
async function handleSplitSubmit(e) {
  e.preventDefault();

  // Show progress
  if (splitProgressSection) {
    splitProgressSection.style.display = 'block';
    splitProgressSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // Submit form naturally (let browser handle file download)
  // Note: We can't track progress for direct form submission
  // Just let the browser handle it
  splitForm.submit();

  // Reset after a delay
  setTimeout(() => {
    if (splitProgressSection) {
      splitProgressSection.style.display = 'none';
    }
  }, 3000);
}

// ==========================================
// UTILITY FUNCTIONS
// ==========================================

/**
 * Detect if device is mobile
 */
function isMobile() {
  return window.innerWidth < 768;
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Validate file size
 */
function validateFileSize(file, maxSizeMB = 50) {
  const maxBytes = maxSizeMB * 1024 * 1024;
  if (file.size > maxBytes) {
    alert(`❌ File quá lớn! Tối đa: ${maxSizeMB}MB (File của bạn: ${formatFileSize(file.size)})`);
    return false;
  }
  return true;
}

// Add file size validation
document.addEventListener('DOMContentLoaded', () => {
  const fileInputs = document.querySelectorAll('input[type="file"]');

  fileInputs.forEach(input => {
    input.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file && !validateFileSize(file)) {
        e.target.value = '';
      }
    });
  });
});

// ==========================================
// RESPONSIVE ADJUSTMENTS
// ==========================================

/**
 * Adjust layout on window resize
 */
window.addEventListener('resize', () => {
  const isMobileView = isMobile();
  // Add responsive adjustments here if needed
});

/**
 * Prevent layout shift on iOS
 */
if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
  document.addEventListener('touchmove', (e) => {
    if (e.target.closest('input, textarea, select, button, a')) {
      return;
    }
  }, false);
}

// ==========================================
// SERVICE WORKER / PWA (Optional)
// ==========================================

/**
 * Register service worker for offline support
 */
if ('serviceWorker' in navigator) {
  // Uncomment when you have a service worker
  // navigator.serviceWorker.register('/static/js/sw.js');
}

// ==========================================
// INITIALIZE
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
  // Log initialization
  console.log('✅ App initialized');

  // Add smooth scroll behavior
  if (window.matchMedia('(prefers-reduced-motion: no-preference)').matches) {
    document.documentElement.style.scrollBehavior = 'smooth';
  }
});

// ==========================================
// ERROR HANDLING
// ==========================================

window.addEventListener('error', (event) => {
  console.error('Global error:', event.error);
  // Could send to error tracking service here
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason);
  // Could send to error tracking service here
});