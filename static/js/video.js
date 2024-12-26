document.addEventListener('DOMContentLoaded', function() {
    const videoFile = document.getElementById('videoFile');
    const convertButton = document.getElementById('convertButton');
    const selectedFileName = document.getElementById('selectedFileName');
    const videoProgress = document.getElementById('videoProgress');
    const videoProgressBar = document.getElementById('videoProgressBar');
    const videoProgressText = document.getElementById('videoProgressText');
    let isConverting = false;

    // File size limit in bytes (500MB)
    const MAX_FILE_SIZE = 500 * 1024 * 1024;

    function updateFileInfo(file) {
        if (file) {
            // Check file size
            if (file.size > MAX_FILE_SIZE) {
                Swal.fire({
                    icon: 'error',
                    title: 'حجم الملف كبير جداً',
                    text: 'الحد الأقصى لحجم الملف هو 500 ميجابايت',
                    confirmButtonText: 'حسناً'
                });
                videoFile.value = '';
                selectedFileName.classList.add('hidden');
                return false;
            }

            // Show selected file name
            selectedFileName.classList.remove('hidden');
            selectedFileName.querySelector('span').textContent = file.name;
            return true;
        }
        selectedFileName.classList.add('hidden');
        return false;
    }

    // Handle file selection
    videoFile.addEventListener('change', function(e) {
        const file = e.target.files[0];
        updateFileInfo(file);
    });

    // Handle file conversion
    convertButton.addEventListener('click', async function() {
        if (isConverting) {
            return;
        }

        const file = videoFile.files[0];
        if (!file) {
            Swal.fire({
                icon: 'warning',
                title: 'لم يتم اختيار ملف',
                text: 'يرجى اختيار ملف فيديو للتحويل',
                confirmButtonText: 'حسناً'
            });
            return;
        }

        // Get selected format
        const format = document.querySelector('input[name="audioFormat"]:checked').value;

        // Create form data
        const formData = new FormData();
        formData.append('file', file);
        formData.append('format', format);

        try {
            isConverting = true;
            convertButton.disabled = true;
            videoProgress.classList.remove('hidden');
            videoProgressBar.style.width = '0%';
            videoProgressText.textContent = 'جاري تحميل الملف...';

            const response = await fetch('/api/video-converter', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'حدث خطأ أثناء التحويل');
            }

            // Get the filename from the Content-Disposition header
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'converted_audio.' + format;
            if (contentDisposition) {
                const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
                if (matches != null && matches[1]) {
                    filename = matches[1].replace(/['"]/g, '');
                }
            }

            // Download the file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            // Show success message
            Swal.fire({
                icon: 'success',
                title: 'تم التحويل بنجاح',
                text: 'تم تحويل الفيديو إلى صوت بنجاح',
                confirmButtonText: 'حسناً'
            });

            // Reset form
            videoFile.value = '';
            selectedFileName.classList.add('hidden');

        } catch (error) {
            console.error('Error:', error);
            Swal.fire({
                icon: 'error',
                title: 'خطأ',
                text: error.message || 'حدث خطأ أثناء التحويل',
                confirmButtonText: 'حسناً'
            });
        } finally {
            isConverting = false;
            convertButton.disabled = false;
            videoProgress.classList.add('hidden');
        }
    });

    // Handle drag and drop
    const dropZone = document.querySelector('.bg-gradient-to-r');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropZone.classList.add('border-indigo-500');
    }

    function unhighlight(e) {
        dropZone.classList.remove('border-indigo-500');
    }

    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        
        if (updateFileInfo(file)) {
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            videoFile.files = dataTransfer.files;
        }
    }
});
