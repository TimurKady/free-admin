(function () {
  const STATE_COLORS = {
    disconnected: '#bdc3c7',
    connecting: '#f1c40f',
    active: '#2ecc71',
    error: '#e74c3c'
  };

  class Card {
    static _adminPrefix = null;

    /**
     * Create a card controller bound to a DOM element.
     * @param {HTMLElement} element - The card container element.
     * @param {{endpoint?: string, stateEndpoint?: string, onEvent?: function, retryDelay?: number}} [options] - Optional configuration.
     */
    constructor(element, options = {}) {
      if (!element) {
        throw new Error('Card requires a DOM element.');
      }

      this.element = element;
      this.options = Object.assign({ retryDelay: 5000 }, options);
      this.adminPrefix = Card._getAdminPrefix(
        this.element.ownerDocument
      );
      this.endpoint = this.options.endpoint || this._inferEndpointFromElement();
      this.cardKey = this.element.dataset.cardKey || null;
      this.onEvent = typeof this.options.onEvent === 'function' ? this.options.onEvent : null;
      this.state = 'disconnected';
      this.eventSource = null;
      this.reconnectTimer = null;
      this.stateListeners = new Set();
      this.stateEndpoint = this._resolveStateEndpoint();
      this.tokenEndpoint = this._resolveTokenEndpoint();
      this._pendingTokenRequest = null;
      this._initialStateFetched = false;
      this._pendingStateRequest = null;
      this._connectionRequested = false;

      this._ensureIndicator();
      this._logEndpointConfiguration();
      this.start();
    }

    /**
     * Start the SSE connection and transition to the "connecting" state.
     */
    start() {
      this._connectionRequested = true;
      this._clearReconnectTimer();
      if (this._initialStateFetched || !this.stateEndpoint) {
        this._openEventSource();
        return;
      }
      this._setState('connecting');
      if (this._pendingStateRequest) {
        return;
      }
      this._pendingStateRequest = this._fetchInitialState().finally(() => {
        this._pendingStateRequest = null;
        this._initialStateFetched = true;
        if (this._connectionRequested) {
          this._openEventSource();
        }
      });
    }

    _logEndpointConfiguration() {
      if (!window || !window.console || typeof window.console.info !== 'function') {
        return;
      }
      const details = {
        cardKey: this.cardKey,
        endpoint: this.endpoint,
        stateEndpoint: this.stateEndpoint || 'n/a'
      };
      window.console.info('[Card] Initialized with endpoints', details);
    }

    /**
     * Stop listening to the SSE endpoint and transition to "disconnected" state.
     */
    stop() {
      this._connectionRequested = false;
      this._clearReconnectTimer();
      this._closeEventSource();
      this._setState('disconnected');
    }

    /**
     * Update the callback that handles incoming SSE payloads.
     * @param {function} callback - The callback invoked with the parsed payload.
     */
    setOnEvent(callback) {
      this.onEvent = typeof callback === 'function' ? callback : null;
    }

    /**
     * Register a listener invoked whenever the connection state changes.
     * @param {(state: string, previousState: string | null, card: Card) => void} listener
     */
    onStateChange(listener) {
      if (typeof listener === 'function') {
        this.stateListeners.add(listener);
      }
    }

    /**
     * Destroy the controller and clean up timers and EventSource instances.
     */
    destroy() {
      this.stop();
      if (this.indicator && this.indicator.parentNode === this.element) {
        this.element.removeChild(this.indicator);
      }
    }

    /**
     * Automatically instantiate cards for elements in the document.
     */
    static bootFromDocument() {
      const doc = document;
      const prefix = Card._getAdminPrefix(doc);
      const elements = doc.querySelectorAll('.card-controller');
      elements.forEach((element) => {
        if (!element.__cardController) {
          const endpoint =
            element.dataset.cardEndpoint ||
            (element.dataset.cardKey
              ? Card._buildEndpoint(prefix, element.dataset.cardKey)
              : undefined);
          element.__cardController = new Card(element, { endpoint });
        }
      });
    }

    _inferEndpointFromElement() {
      const { cardEndpoint, cardKey } = this.element.dataset;
      if (cardEndpoint) {
        return cardEndpoint;
      }
      if (cardKey) {
        return Card._buildEndpoint(this.adminPrefix, cardKey);
      }
      throw new Error('Card requires an SSE endpoint or data-card-key attribute.');
    }

    static _buildEndpoint(prefix, cardKey) {
      return Card._buildPublicEndpoint(cardKey);
    }

    static _buildStateEndpoint(prefix, cardKey) {
      const normalized = Card._normalizePrefix(prefix);
      return `${normalized}/api/cards/${cardKey}/state`;
    }

    static _buildTokenEndpoint(prefix, cardKey) {
      const normalized = Card._normalizePrefix(prefix);
      return `${normalized}/api/cards/${cardKey}/events/token`;
    }

    static _buildPublicEndpoint(cardKey) {
      return `/api/cards/${cardKey}/events`;
    }

    static _getAdminPrefix(doc) {
      if (Card._adminPrefix !== null) {
        return Card._adminPrefix;
      }
      const resolved = Card._resolveAdminPrefix(doc);
      Card._adminPrefix = resolved;
      return resolved;
    }

    static _resolveAdminPrefix(doc) {
      const documentRef = doc || document;
      const body = documentRef && documentRef.body;
      if (body && body.dataset && typeof body.dataset.adminPrefix === 'string') {
        const direct = Card._normalizePrefix(body.dataset.adminPrefix);
        if (direct || body.dataset.adminPrefix === '' || body.dataset.adminPrefix === '/') {
          return direct;
        }
      }
      if (window.ADMIN_API && typeof window.ADMIN_API.prefix === 'string') {
        const fallback = Card._stripApiSuffix(window.ADMIN_API.prefix);
        return Card._normalizePrefix(fallback);
      }
      return '';
    }

    static _normalizePrefix(prefix) {
      if (typeof prefix !== 'string') {
        return '';
      }
      const trimmed = prefix.trim();
      if (!trimmed || trimmed === '/') {
        return '';
      }
      const ensured = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
      return ensured.replace(/\/+$/, '');
    }

    static _stripApiSuffix(value) {
      if (typeof value !== 'string') {
        return '';
      }
      const sanitized = value.trim();
      if (!sanitized) {
        return '';
      }
      const apiMatch = sanitized.match(/^(.*?)(\/api(?:\b|\/|$).*)$/);
      if (apiMatch && apiMatch[1] !== undefined) {
        return apiMatch[1];
      }
      const withoutTrailing = sanitized.replace(/\/+$/, '');
      const lastSlash = withoutTrailing.lastIndexOf('/');
      if (lastSlash <= 0) {
        return '';
      }
      return withoutTrailing.slice(0, lastSlash);
    }

    _openEventSource() {
      if (!this.endpoint) {
        throw new Error('Card cannot connect without an endpoint.');
      }

      this._setState('connecting');
      this._closeEventSource();

      this._fetchEventToken()
        .then((token) => {
          if (!this._connectionRequested) {
            return;
          }

          const url = this._composeEventSourceUrl(token);

          try {
            this.eventSource = new EventSource(url);
          } catch (error) {
            console.error('Card failed to create EventSource:', error);
            this._handleError(error);
            return;
          }

          this.eventSource.addEventListener('open', () => {
            this._setState('active');
          });

          this.eventSource.addEventListener('message', (event) => {
            this._handleMessage(event);
          });

          this.eventSource.addEventListener('error', (event) => {
            this._handleError(event);
          });
        })
        .catch((error) => {
          console.error('Card failed to obtain event token:', error);
          this._handleError(error);
        });
    }

    _resolveStateEndpoint() {
      if (this.options.stateEndpoint) {
        return this.options.stateEndpoint;
      }
      if (this.cardKey) {
        return Card._buildStateEndpoint(this.adminPrefix, this.cardKey);
      }
      return null;
    }

    _resolveTokenEndpoint() {
      if (this.options.tokenEndpoint) {
        return this.options.tokenEndpoint;
      }
      const { cardTokenEndpoint } = this.element.dataset;
      if (cardTokenEndpoint) {
        return cardTokenEndpoint;
      }
      if (this.cardKey) {
        return Card._buildTokenEndpoint(this.adminPrefix, this.cardKey);
      }
      return null;
    }

    _fetchInitialState() {
      if (!this.stateEndpoint) {
        return Promise.resolve(null);
      }
      const request = window.fetch(this.stateEndpoint, {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' }
      });
      return request
        .then((response) => {
          if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
          }
          return response.text();
        })
        .then((text) => {
          if (!text) {
            return null;
          }
          try {
            return JSON.parse(text);
          } catch (error) {
            throw new Error('Invalid JSON in state response');
          }
        })
        .then((data) => {
          if (!data || (data && data.status === 'no-data')) {
            this._handleNoDataState();
            return null;
          }
          const payload = typeof data === 'string' ? data : JSON.stringify(data);
          this._handleMessage({ data: payload });
          return data;
        })
        .catch((error) => {
          console.error('Card failed to load initial state:', error);
          return null;
        });
    }

    _handleNoDataState() {
      this._handleMessage({ data: 'null' });
    }

    _closeEventSource() {
      if (this.eventSource) {
        this.eventSource.close();
        this.eventSource = null;
      }
    }

    _handleMessage(event) {
      if (!event || typeof event.data !== 'string') {
        return;
      }

      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch (error) {
        console.error('Card failed to parse SSE payload:', error);
        return;
      }

      if (this.onEvent) {
        try {
          this.onEvent(payload, this);
        } catch (error) {
          console.error('Card onEvent callback error:', error);
        }
      }
    }

    _handleError(error) {
      console.error('Card encountered an error:', error);
      const nextState = this._connectionRequested ? 'disconnected' : 'error';
      this._setState(nextState);
      this._closeEventSource();
      this._scheduleReconnect();
    }

    _composeEventSourceUrl(token) {
      if (!token) {
        return this.endpoint;
      }
      try {
        const base = new URL(this.endpoint, window.location.origin);
        base.searchParams.set('token', token);
        return base.toString();
      } catch (error) {
        const joiner = this.endpoint.includes('?') ? '&' : '?';
        return `${this.endpoint}${joiner}token=${encodeURIComponent(token)}`;
      }
    }

    _fetchEventToken() {
      if (!this.tokenEndpoint) {
        return Promise.resolve(null);
      }
      if (this._pendingTokenRequest) {
        return this._pendingTokenRequest;
      }

      const request = window
        .fetch(this.tokenEndpoint, {
          credentials: 'same-origin',
          headers: { Accept: 'application/json' }
        })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`Token request failed with status ${response.status}`);
          }
          return response.json();
        })
        .then((payload) => {
          if (!payload || typeof payload.token !== 'string') {
            throw new Error('Token response did not include a token');
          }
          return payload.token;
        })
        .finally(() => {
          this._pendingTokenRequest = null;
        });

      this._pendingTokenRequest = request;
      return request;
    }

    _scheduleReconnect() {
      this._clearReconnectTimer();
      this.reconnectTimer = window.setTimeout(() => {
        this.start();
      }, this.options.retryDelay);
    }

    _clearReconnectTimer() {
      if (this.reconnectTimer) {
        window.clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    }

    _getIndicatorContainer() {
      const cardContainer = this.element.closest('.card');
      if (!cardContainer) {
        return null;
      }
      return (
        cardContainer.querySelector('.card-controller__status') ||
        cardContainer.querySelector('.card-header') ||
        null
      );
    }

    _ensureIndicator() {
      if (!this.element.classList.contains('card-controller')) {
        this.element.classList.add('card-controller');
      }

      const indicator = document.createElement('span');
      indicator.className = 'card-controller__indicator';
      Object.assign(indicator.style, {
        display: 'block',
        width: '12px',
        height: '12px',
        borderRadius: '50%',
        backgroundColor: STATE_COLORS[this.state],
        boxShadow: '0 0 4px rgba(0, 0, 0, 0.3)',
        position: 'absolute',
        right: '12px'
      });

      if (this.indicator && this.indicator.parentNode) {
        this.indicator.parentNode.removeChild(this.indicator);
      }

      this.indicator = indicator;
      const container = this._getIndicatorContainer();
      if (container) {
        if (typeof window !== 'undefined' && window.getComputedStyle) {
          const position = window.getComputedStyle(container).position;
          if (!position || position === 'static') {
            container.style.position = 'relative';
          }
        } else if (!container.style.position) {
          container.style.position = 'relative';
        }
        container.appendChild(indicator);
        return;
      }
      if (typeof window !== 'undefined' && window.getComputedStyle) {
        const position = window.getComputedStyle(this.element).position;
        if (!position || position === 'static') {
          this.element.style.position = 'relative';
        }
      } else if (!this.element.style.position) {
        this.element.style.position = 'relative';
      }
      this.element.appendChild(indicator);
    }

    _setState(state) {
      if (this.state === state) {
        return;
      }
      const previousState = this.state;
      this.state = state;
      if (this.indicator) {
        this.indicator.style.backgroundColor = STATE_COLORS[state] || STATE_COLORS.disconnected;
      }
      this.element.dataset.cardState = state;
      this._notifyStateChange(state, previousState);
    }

    _notifyStateChange(state, previousState) {
      this.stateListeners.forEach((listener) => {
        try {
          listener(state, previousState, this);
        } catch (error) {
          console.error('Card state listener error:', error);
        }
      });
    }
  }

  window.Card = Card;

  const applyCustomCardBehavior = (card) => {
    if (!card || !card.element) {
      return;
    }
    if (card.element.dataset.cardKey !== 'thermo1') {
      return;
    }
    if (card.element.dataset.thermoReady === 'true') {
      return;
    }

    const display = card.element.querySelector('[data-thermo-display]');
    if (!display) {
      return;
    }

    const defaultText = display.textContent;
    const setDefaultText = () => {
      display.textContent = defaultText;
      display.classList.remove('text-danger');
      display.classList.add('text-secondary');
    };
    const showNoData = () => {
      display.textContent = 'No data';
      display.classList.remove('text-danger');
      display.classList.add('text-secondary');
    };
    const applyColor = (value) => {
      if (value > 36) {
        display.classList.remove('text-secondary');
        display.classList.add('text-danger');
      } else {
        display.classList.remove('text-danger');
        display.classList.add('text-secondary');
      }
    };

    let hasReading = false;

    card.setOnEvent((payload) => {
      if (!payload || typeof payload.temp === 'undefined') {
        hasReading = false;
        showNoData();
        return;
      }
      const temp = Number(payload.temp);
      if (!Number.isFinite(temp)) {
        hasReading = false;
        showNoData();
        return;
      }
      hasReading = true;
      display.textContent = `Temperature: ${temp.toFixed(1)} °C`;
      applyColor(temp);
    });

    card.onStateChange((state) => {
      if (state !== 'active') {
        hasReading = false;
        showNoData();
      } else if (!hasReading) {
        setDefaultText();
      }
    });

    card.element.dataset.thermoReady = 'true';
  };

  const boot = () => {
    Card.bootFromDocument();
    const elements = document.querySelectorAll('.card-controller');
    elements.forEach((element) => {
      const card = element.__cardController;
      if (card) {
        applyCustomCardBehavior(card);
      }
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
