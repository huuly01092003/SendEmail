document.addEventListener("DOMContentLoaded", () => {
  
  // ==========================================
  // THEME MANAGEMENT
  // ==========================================
  const themeButtons = document.querySelectorAll(".theme-switcher button");
  const storedTheme = localStorage.getItem("app-theme") || "aurora";

  function setTheme(theme) {
    document.body.dataset.theme = theme;
    localStorage.setItem("app-theme", theme);
    themeButtons.forEach(btn => {
      btn.classList.toggle("active", btn.dataset.theme === theme);
    });
  }

  themeButtons.forEach(button => {
    button.addEventListener("click", () => {
      setTheme(button.dataset.theme);
    });
  });

  setTheme(storedTheme);

  // ==========================================
  // FILE INPUT HANDLER
  // ==========================================
  const fileInputs = document.querySelectorAll('input[type="file"]');
  fileInputs.forEach(input => {
    input.addEventListener('change', (e) => {
      const fileGroup = e.target.closest('.file-group');
      const fileNameSpan = fileGroup?.querySelector('.file-name');
      
      if (input.id === 'excel-files') {
        const count = e.target.files.length;
        fileNameSpan.textContent = count > 0 ? `✅ ${count} file được chọn` : "Chưa chọn file...";
        
        const countDiv = document.getElementById('file-count');
        if (count > 0) {
          document.getElementById('count-text').textContent = count;
          countDiv.style.display = 'block';
        } else {
          countDiv.style.display = 'none';
        }
      } else {
        const file = e.target.files[0];
        if (file) {
          if (!validateFileSize(file, 50)) {
            e.target.value = '';
            fileNameSpan.textContent = "File quá lớn! (Max 50MB)";
            fileNameSpan.style.color = "var(--danger)";
            return;
          }
          fileNameSpan.textContent = file.name;
          fileNameSpan.style.color = "var(--text-color)";
        } else {
          fileNameSpan.textContent = "Chưa chọn file...";
          fileNameSpan.style.color = "var(--text-color-muted)";
        }
      }
    });

    const fileNameSpan = input.closest('.file-group')?.querySelector('.file-name');
    if (fileNameSpan) {
      fileNameSpan.addEventListener('click', () => {
        input.click();
      });
    }
  });

  function validateFileSize(file, maxSizeMB = 50) {
    const maxBytes = maxSizeMB * 1024 * 1024;
    return file.size <= maxBytes;
  }

  // ==========================================
  // SPLIT FORM - LOAD SHEETS
  // ==========================================
  const splitFileInput = document.getElementById('split-file');
  const sheetSelect = document.getElementById('sheet-select');
  const sheetGroup = document.getElementById('sheet-group');

  if (splitFileInput && sheetSelect && sheetGroup) {
    splitFileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) {
        sheetGroup.style.display = 'none';
        return;
      }

      showLoading("Đang đọc file Excel...");

      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('/get_sheets', {
          method: 'POST',
          body: formData
        });

        const result = await response.json();
        
        if (result.sheets) {
          sheetSelect.innerHTML = '<option value="">-- Chọn Sheet --</option>';
          result.sheets.forEach(sheet => {
            const option = document.createElement('option');
            option.value = sheet;
            option.textContent = sheet;
            sheetSelect.appendChild(option);
          });
          sheetGroup.style.display = 'block';
        } else if (result.error) {
          alert('❌ Lỗi: ' + result.error);
        }

        hideLoading();
      } catch (error) {
        hideLoading();
        alert('❌ Lỗi đọc file: ' + error.message);
      }
    });
  }

  // ==========================================
  // SPLIT FORM SUBMIT
  // ==========================================
  const splitForm = document.getElementById("splitForm");
  
  if (splitForm) {
    splitForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      
      const sheetName = document.getElementById('sheet-select')?.value;
      const splitColumn = document.getElementById('split-column')?.value;
      const templateEndRow = document.getElementById('template-end-row')?.value;
      const startRow = document.getElementById('data-start-row')?.value;
      const endRow = document.getElementById('data-end-row')?.value;
      
      if (!sheetName) {
        alert('❌ Vui lòng chọn Sheet!');
        return;
      }
      if (!splitColumn) {
        alert('❌ Vui lòng nhập Tên Cột Cần Chia!');
        return;
      }
      if (!templateEndRow || !startRow || !endRow) {
        alert('❌ Vui lòng nhập đầy đủ các dòng (Template, Dữ liệu đầu, Dữ liệu cuối)!');
        return;
      }
      
      showLoading("Đang tách file...");

      const formData = new FormData(splitForm);

      try {
        const response = await fetch('/split', {
          method: 'POST',
          body: formData
        });

        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'tach_file.zip';
          a.click();
          hideLoading();
          alert('✅ Tách file thành công!');
        } else {
          const error = await response.text();
          hideLoading();
          alert('❌ ' + error);
        }
      } catch (error) {
        hideLoading();
        alert('❌ Lỗi: ' + error.message);
      }
    });
  }

  // ==========================================
  // EMAIL FORM - UPLOAD FOLDER
  // ==========================================
  const excelFilesInput = document.getElementById('excel-files');
  let uploadedFolderId = null;

  if (excelFilesInput) {
    excelFilesInput.addEventListener('change', async (e) => {
      const files = e.target.files;
      if (!files || files.length === 0) {
        uploadedFolderId = null;
        return;
      }

      showLoading(`Đang tải ${files.length} file...`);

      const formData = new FormData();
      for (let file of files) {
        formData.append('files', file);
      }

      try {
        const response = await fetch('/upload_folder', {
          method: 'POST',
          body: formData
        });

        const result = await response.json();

        if (result.success) {
          uploadedFolderId = result.folder_id;
          hideLoading();
        } else {
          hideLoading();
          alert('❌ ' + (result.error || 'Upload lỗi'));
        }
      } catch (error) {
        hideLoading();
        alert('❌ ' + error.message);
      }
    });
  }

  // ==========================================
  // EMAIL FORM SUBMIT
  // ==========================================
  const emailForm = document.getElementById("emailForm");
  const submitBtn = document.getElementById("submitBtn");
  const progressSection = document.getElementById("progressSection");
  const progressFill = document.getElementById("progressFill");
  const progressText = document.getElementById("progressText");
  const downloadBtn = document.getElementById("downloadBtn");

  if (emailForm) {
    emailForm.addEventListener("submit", handleEmailSubmit);
  }

  async function handleEmailSubmit(e) {
    e.preventDefault();

    if (!uploadedFolderId) {
      alert('❌ Vui lòng chọn file Excel trước!');
      return;
    }

    showLoading("Đang tải lên và khởi tạo...");
    submitBtn.disabled = true;
    submitBtn.textContent = "⏳ Đang gửi...";
    progressSection.style.display = "none";
    downloadBtn.style.display = "none";

    const formData = new FormData(emailForm);
    formData.append('folder_id', uploadedFolderId);

    try {
      const response = await fetch("/send_emails", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (!response.ok || result.error) {
        showError("❌ Lỗi: " + (result.error || `Server error ${response.status}`));
        resetEmailForm();
        return;
      }

      const jobId = result.job_id;
      progressSection.style.display = "flex";
      progressText.textContent = "Đang chuẩn bị gửi...";
      
      hideLoading();

      if (window.innerWidth < 768) {
        progressSection.scrollIntoView({ behavior: "smooth", block: "center" });
      }

      await pollEmailStatus(jobId);

    } catch (error) {
      showError("❌ Lỗi kết nối: " + error.message);
      resetEmailForm();
    }
  }

  // ==========================================
  // POLLING EMAIL STATUS
  // ==========================================
  async function pollEmailStatus(jobId) {
    let intervalId = setInterval(async () => {
      try {
        const statusResponse = await fetch(`/check_status/${jobId}`);
        const status = await statusResponse.json();

        if (status.status === "processing") {
          updateProgress(status);
        } else if (status.status === "completed") {
          clearInterval(intervalId);
          completeEmailSending(jobId);
        } else if (status.status === "failed") {
          clearInterval(intervalId);
          showError("❌ Gửi email thất bại! " + (status.error || ""));
          resetEmailForm();
        }
      } catch (error) {
        console.error("Polling error:", error);
        clearInterval(intervalId);
        showError("❌ Mất kết nối.");
        resetEmailForm();
      }
    }, 2000);
  }

  function updateProgress(status) {
    const progress = status.total > 0 ? Math.round((status.progress / status.total) * 100) : 0;
    progressFill.style.width = progress + "%";
    progressFill.textContent = progress + "%";
    progressText.textContent = `Đã gửi ${status.progress}/${status.total} email...`;
  }

  function completeEmailSending(jobId) {
    progressFill.style.width = "100%";
    progressFill.style.backgroundColor = "var(--success)";
    progressFill.textContent = "100%";
    progressText.textContent = "✅ Hoàn tất! Tải file log bên dưới.";

    downloadBtn.style.display = "block";
    downloadBtn.onclick = () => {
      window.location.href = `/download_log/${jobId}`;
    };

    resetEmailForm();
  }

  function resetEmailForm() {
    hideLoading();
    submitBtn.disabled = false;
    submitBtn.textContent = "🚀 Gửi Email Tự Động";
    progressFill.style.backgroundColor = "var(--primary)";
  }

  function showError(message) {
    hideLoading();
    alert(message);
    progressSection.style.display = "none";
  }

  function showLoading(text) {
    document.getElementById('loading-text').textContent = text || "Đang xử lý...";
    document.getElementById('loading-overlay').classList.add("active");
  }

  function hideLoading() {
    document.getElementById('loading-overlay').classList.remove("active");
  }

  console.log("✅ Ứng dụng khởi tạo thành công!");

});