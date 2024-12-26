// FileFlow Translation System
class TranslationManager {
    constructor() {
        this.translations = {};
        this.currentLanguage = 'ar';
        this.supportedLanguages = ['ar', 'en', 'fr'];
        this.defaultLanguage = 'ar';
        this.isLoading = false;
        this.observers = new Set();
    }

    async initialize() {
        try {
            this.isLoading = true;
            const response = await fetch('/static/js/translations.json');
            this.translations = await response.json();
            
            // Get user's preferred language from localStorage or browser
            const savedLang = localStorage.getItem('preferred_language');
            const browserLang = navigator.language.split('-')[0];
            const initialLang = this.supportedLanguages.includes(savedLang) ? savedLang :
                              this.supportedLanguages.includes(browserLang) ? browserLang :
                              this.defaultLanguage;
            
            await this.setLanguage(initialLang);
            this.setupLanguageSelector();
            this.isLoading = false;
        } catch (error) {
            console.error('Error initializing translations:', error);
            this.isLoading = false;
        }
    }

    setupLanguageSelector() {
        const selector = document.getElementById('languageSelector');
        if (selector) {
            selector.value = this.currentLanguage;
            selector.addEventListener('change', (e) => this.setLanguage(e.target.value));
        }
    }

    async setLanguage(lang) {
        if (!this.supportedLanguages.includes(lang)) {
            console.error(`Unsupported language: ${lang}`);
            return;
        }

        this.currentLanguage = lang;
        localStorage.setItem('preferred_language', lang);
        
        // Update HTML attributes
        document.documentElement.lang = lang;
        document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
        
        // Update layout direction classes
        document.body.classList.remove('rtl', 'ltr');
        document.body.classList.add(lang === 'ar' ? 'rtl' : 'ltr');
        
        // Update all translations
        this.updateAllTranslations();
        
        // Notify observers
        this.notifyObservers();
    }

    updateAllTranslations() {
        this.updateGeneralTranslations();
        this.updateMenuTranslations();
        this.updateHeroSection();
        this.updateServicesSection();
        this.updateFeaturesSection();
        this.updateContactForm();
        this.updateMetaTags();
    }

    updateGeneralTranslations() {
        document.querySelectorAll('[data-translate]').forEach(element => {
            const key = element.getAttribute('data-translate');
            const translation = this.getTranslation(key);
            if (translation) {
                if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                    element.placeholder = translation;
                } else {
                    element.textContent = translation;
                }
            }
        });
    }

    updateMenuTranslations() {
        document.querySelectorAll('[data-menu]').forEach(element => {
            const key = element.getAttribute('data-menu');
            const translation = this.getTranslation(`menu.${key}`);
            if (translation) {
                element.textContent = translation;
            }
        });
    }

    updateHeroSection() {
        const heroElements = {
            title: document.querySelector('[data-hero="title"]'),
            description: document.querySelector('[data-hero="description"]'),
            startNow: document.querySelector('[data-hero="start-now"]'),
            learnFeatures: document.querySelector('[data-hero="learn-features"]')
        };

        Object.entries(heroElements).forEach(([key, element]) => {
            if (element) {
                const translation = this.getTranslation(`hero.${key}`);
                if (translation) {
                    element.textContent = translation;
                }
            }
        });
    }

    updateServicesSection() {
        const services = this.translations.website.services;
        const container = document.querySelector('#services .grid');
        
        if (container) {
            container.innerHTML = services.map((service, index) => `
                <div class="service-card rounded-xl p-6 text-center" data-service="${index}">
                    <div class="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        ${this.getServiceIcon(index)}
                    </div>
                    <h3 class="text-xl font-semibold mb-3">${service.title[this.currentLanguage]}</h3>
                    <p class="text-gray-600">${service.description[this.currentLanguage]}</p>
                </div>
            `).join('');
        }
    }

    updateFeaturesSection() {
        const features = this.translations.website.features;
        const container = document.querySelector('#features .grid');
        
        if (container) {
            container.innerHTML = features.advantages.map((advantage, index) => `
                <div class="group" data-aos="fade-up" data-aos-delay="${100 * (index + 1)}">
                    <div class="bg-white/80 backdrop-blur-xl p-8 rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.06)] transition-all duration-300 hover:shadow-[0_8px_30px_rgb(99,102,241,0.1)] hover:-translate-y-2">
                        <h3 class="text-xl font-semibold mb-4">${advantage.title[this.currentLanguage]}</h3>
                        <p class="text-gray-600">${advantage.description[this.currentLanguage]}</p>
                    </div>
                </div>
            `).join('');
        }
    }

    updateContactForm() {
        const form = this.translations.website.contact.form;
        const elements = {
            name: document.querySelector('[data-contact="name"]'),
            email: document.querySelector('[data-contact="email"]'),
            subject: document.querySelector('[data-contact="subject"]'),
            message: document.querySelector('[data-contact="message"]'),
            submit: document.querySelector('[data-contact="submit"]')
        };

        Object.entries(elements).forEach(([key, element]) => {
            if (element) {
                const translation = form[key][this.currentLanguage];
                if (translation) {
                    if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                        element.placeholder = translation;
                    }
                    element.textContent = translation;
                }
            }
        });
    }

    updateMetaTags() {
        // Update meta tags for SEO
        const title = this.getTranslation('title');
        const description = this.getTranslation('hero.description');
        
        document.title = title;
        document.querySelector('meta[name="description"]')?.setAttribute('content', description);
        document.querySelector('meta[property="og:title"]')?.setAttribute('content', title);
        document.querySelector('meta[property="og:description"]')?.setAttribute('content', description);
    }

    getTranslation(key) {
        try {
            const keys = key.split('.');
            let value = this.translations.website;
            
            for (const k of keys) {
                value = value[k];
                if (!value) return null;
            }
            
            return typeof value === 'object' ? value[this.currentLanguage] : value;
        } catch (error) {
            console.warn(`Translation not found for key: ${key}`);
            return null;
        }
    }

    getServiceIcon(index) {
        const icons = [
            '<svg class="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/></svg>',
            '<svg class="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-.553.894L16 18l-4.447-2.276A1 1 0 0111 14.618V8.618a1 1 0 01.553-.894L16 6l4.447 2.276A1 1 0 0121 8.618v6.764a1 1 0 01-.553.894L16 18l-4.447-2.276A1 1 0 0111 14.618V8.618a1 1 0 01.553-.894L16 6"/></svg>',
            '<svg class="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>',
            '<svg class="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>'
        ];
        return icons[index] || icons[0];
    }

    subscribe(callback) {
        this.observers.add(callback);
    }

    unsubscribe(callback) {
        this.observers.delete(callback);
    }

    notifyObservers() {
        this.observers.forEach(callback => callback(this.currentLanguage));
    }
}

// Initialize the translation manager
const translationManager = new TranslationManager();

// When the DOM is loaded, initialize translations
document.addEventListener('DOMContentLoaded', () => {
    translationManager.initialize();
});

// Export for global access
window.translationManager = translationManager;
