document.addEventListener('DOMContentLoaded', function() {
    const contactForm = document.getElementById('contactForm');
    
    if (contactForm) {
        contactForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // إظهار رسالة "جاري الإرسال"
            showMessage('جاري إرسال الرسالة...', 'info');
            
            const formData = {
                name: contactForm.querySelector('[name="name"]').value,
                email: contactForm.querySelector('[name="email"]').value,
                subject: contactForm.querySelector('[name="subject"]').value,
                message: contactForm.querySelector('[name="message"]').value
            };
            
            try {
                const response = await fetch('/api/contact', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                console.log('Server Response:', result);
                
                if (result.success) {
                    showMessage(result.message, 'success');
                    contactForm.reset();
                } else {
                    showMessage(result.message || 'حدث خطأ أثناء إرسال الرسالة', 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showMessage('حدث خطأ في الاتصال بالخادم', 'error');
            }
        });
    }
    
    // دالة لعرض الرسائل
    function showMessage(message, type) {
        // إنشاء عنصر div للرسالة إذا لم يكن موجوداً
        let messageDiv = document.getElementById('contact-message');
        if (!messageDiv) {
            messageDiv = document.createElement('div');
            messageDiv.id = 'contact-message';
            messageDiv.style.marginTop = '1rem';
            messageDiv.style.padding = '1rem';
            messageDiv.style.borderRadius = '0.5rem';
            messageDiv.style.textAlign = 'center';
            contactForm.insertAdjacentElement('afterend', messageDiv);
        }
        
        // تعيين لون الخلفية حسب نوع الرسالة
        switch(type) {
            case 'success':
                messageDiv.style.backgroundColor = '#dcfce7';
                messageDiv.style.color = '#166534';
                break;
            case 'error':
                messageDiv.style.backgroundColor = '#fee2e2';
                messageDiv.style.color = '#991b1b';
                break;
            case 'info':
                messageDiv.style.backgroundColor = '#dbeafe';
                messageDiv.style.color = '#1e40af';
                break;
        }
        
        messageDiv.textContent = message;
        
        // إخفاء الرسالة بعد 5 ثوانٍ
        if (type !== 'info') {
            setTimeout(() => {
                messageDiv.remove();
            }, 5000);
        }
    }
});
