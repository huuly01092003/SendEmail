/**
 * APP.JS - Logic xử lý giao diện
 * Bao gồm:
 * 1. Khởi tạo Theme (Sáng/Tối/Aurora)
 * 2. Xử lý Form (Floating Labels & File Inputs)
 * 3. Xử lý Form Tách File (Split Form)
 * 4. Xử lý Form Gửi Email (Email Form)
 * 5. Theo dõi tiến độ (Polling)
 * 6. Các hàm tiện ích (UI Helpers)
 */

document.addEventListener("DOMContentLoaded", () => {
  
  // ==========================================
  // 1. KHỞI TẠO THEME
  // ==========================================
  const themeButtons = document.querySelectorAll(".theme-switcher button");
  const storedTheme = localStorage.getItem("app-theme") || "aurora"; // Mặc định là 'aurora'

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

  // Kích hoạt theme đã lưu khi tải trang
  setTheme(storedTheme);

  // ==========================================
  // 2. XỬ LÝ FORM CHUNG (FILE INPUTS)
  // ==========================================
  const fileInputs = document.querySelectorAll('input[type="file"]');
  fileInputs.forEach(input => {
    input.addEventListener('change', (e) => {
      const fileNameSpan = e.target.closest('.file-group').querySelector('.file-name');
      const file = e.target.files[0];
      if (file) {
        // Validate file size
        if (!validateFileSize(file, 50)) { // 50MB limit
          e.target.value = ''; // Clear input
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
    });
    // Kích hoạt label khi click vào span
    const fileNameSpan = input.closest('.file-group').querySelector('.file-name');
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
  // 3. XỬ LÝ FORM TÁCH FILE
  // ==========================================
  const splitForm = document.getElementById("splitForm");
  const loadingOverlay = document.getElementById("loading-overlay");
  const loadingText = document.getElementById("loading-text");

  if (splitForm) {
    splitForm.addEventListener("submit", () => {
      // Không dùng e.preventDefault() để trình duyệt xử lý download
      showLoading("Đang tách file, vui lòng chờ...");

      // Tự động ẩn loading sau 8s phòng trường hợp lỗi
      // (Trình duyệt sẽ tự xử lý việc tải file về)
      setTimeout(hideLoading, 8000);
    });
  }

  // ==========================================
  // 4. XỬ LÝ FORM GỬI EMAIL
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

    // Hiển thị giao diện loading
    showLoading("Đang tải file lên và khởi tạo...");
    submitBtn.disabled = true;
    submitBtn.textContent = "⏳ Đang gửi...";
    progressSection.style.display = "none";
    downloadBtn.style.display = "none";

    const formData = new FormData(emailForm);

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

      // Bắt đầu theo dõi tiến độ
      const jobId = result.job_id;
      progressSection.style.display = "flex";
      progressText.textContent = "Đang chuẩn bị gửi...";
      
      // Ẩn loading overlay để hiện progress bar
      hideLoading();

      // Cuộn xuống thanh progress trên di động
      if (window.innerWidth < 768) {
        progressSection.scrollIntoView({ behavior: "smooth", block: "center" });
      }

      // Bắt đầu Polling
      await pollEmailStatus(jobId);

    } catch (error) {
      showError("❌ Lỗi kết nối: " + error.message);
      resetEmailForm();
    }
  }

  // ==========================================
  // 5. THEO DÕI TIẾN ĐỘ (POLLING)
  // ==========================================
  // (Logic này lấy từ file app.js của bạn, rất tốt!)
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
        console.error("Lỗi polling:", error);
        clearInterval(intervalId);
        showError("❌ Mất kết nối khi đang kiểm tra tiến độ.");
        resetEmailForm();
      }
    }, 2000); // 2 giây 1 lần
  }

  // ==========================================
  // 6. CÁC HÀM TIỆN ÍCH (UI HELPERS)
  // ==========================================

  function updateProgress(status) {
    const progress = status.total > 0 ? Math.round((status.progress / status.total) * 100) : 0;
    progressFill.style.width = progress + "%";
    progressFill.textContent = progress + "%";
    progressText.textContent = `Đã gửi ${status.progress}/${status.total} email...`;
  }

  function completeEmailSending(jobId) {
    progressFill.style.width = "100%";
    progressFill.style.backgroundColor = "var(--success)"; // Đổi màu xanh
    progressFill.textContent = "100%";
    progressText.textContent = "✅ Hoàn tất! Nhấn nút bên dưới để tải file log.";

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
    progressFill.style.backgroundColor = "var(--primary)"; // Reset màu
  }

  function showError(message) {
    hideLoading();
    alert(message); // Dùng alert đơn giản nhưng hiệu quả
    progressSection.style.display = "none";
  }

  function showLoading(text) {
    loadingText.textContent = text || "Đang xử lý...";
    loadingOverlay.classList.add("active");
  }

  function hideLoading() {
    loadingOverlay.classList.remove("active");
  }

  console.log("✅ Ứng dụng đã khởi tạo thành công!");

}); // Hết DOMContentLoaded