// Color Palette Switcher
const PaletteSwitcher = {
  init() {
    this.createUI();
    this.setupEventListeners();
  },

  createUI() {
    const container = document.createElement('div');
    container.id = 'palette-switcher';
    container.innerHTML = `
      <div class="palette-toggle">🎨</div>
      <div class="palette-menu">
        <button data-palette="palette1" title="Purple Pink" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"></button>
        <button data-palette="palette2" title="Cyan Purple" style="background: linear-gradient(135deg, #00d2fc 0%, #3a47d5 100%);"></button>
        <button data-palette="palette3" title="Ocean" style="background: linear-gradient(135deg, #0077be 0%, #00c9ff 100%);"></button>
        <button data-palette="palette4" title="Sunset" style="background: linear-gradient(135deg, #ff6b6b 0%, #ffd93d 100%);"></button>
        <button data-palette="palette5" title="Forest" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);"></button>
      </div>
    `;
    document.body.appendChild(container);
  },

  setupEventListeners() {
    const toggle = document.querySelector('.palette-toggle');
    const menu = document.querySelector('.palette-menu');
    const buttons = document.querySelectorAll('.palette-menu button');

    toggle.addEventListener('click', () => {
      menu.classList.toggle('active');
      toggle.classList.toggle('active');
    });

    buttons.forEach(button => {
      button.addEventListener('click', (e) => {
        const paletteKey = e.target.dataset.palette;
        if (window.intelliprepBg) {
          window.intelliprepBg.changePalette(paletteKey);
        }
        
        // Save preference
        localStorage.setItem('selectedPalette', paletteKey);
        
        // Visual feedback
        buttons.forEach(b => b.classList.remove('active'));
        button.classList.add('active');
      });
    });

    // Load saved palette
    const savedPalette = localStorage.getItem('selectedPalette');
    if (savedPalette) {
      document.querySelector(`[data-palette="${savedPalette}"]`).classList.add('active');
      setTimeout(() => {
        if (window.intelliprepBg) {
          window.intelliprepBg.changePalette(savedPalette);
        }
      }, 100);
    } else {
      document.querySelector('[data-palette="palette1"]').classList.add('active');
    }
  }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    PaletteSwitcher.init();
  });
} else {
  PaletteSwitcher.init();
}