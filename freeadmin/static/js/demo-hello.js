(() => {
  'use strict';

  class DemoHelloController {
    constructor() {
      this._selector = '[data-page-message]';
      this._badgeClass = 'badge rounded-pill text-bg-primary ms-2';
      this._boundAttribute = 'data-demo-hello-bound';
    }

    init() {
      const messageNode = document.querySelector(this._selector);
      if (!messageNode || messageNode.hasAttribute(this._boundAttribute)) {
        return;
      }
      messageNode.setAttribute(this._boundAttribute, 'true');
      const badge = this._buildBadge();
      messageNode.insertAdjacentElement('beforeend', badge);
    }

    _buildBadge() {
      const badge = document.createElement('span');
      badge.className = this._badgeClass;
      badge.textContent = 'JS сonnected';
      return badge;
    }
  }

  window.addEventListener('DOMContentLoaded', () => {
    new DemoHelloController().init();
  });
})();
