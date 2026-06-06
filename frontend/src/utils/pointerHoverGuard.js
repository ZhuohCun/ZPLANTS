const SUPPRESS_CLASS = 'suppress-pointer-hover'
const interactiveSelector = 'button, .el-button, .nav-button, .quick-card, .zone-pick-card, .upload-trigger-card, .header-action-compact, .header-mini-btn, .rule-card-toggle, .drawer-link'
let lastPointerType = 'mouse'

function docRoot() {
  return document.documentElement
}

function addSuppression() {
  docRoot().classList.add(SUPPRESS_CLASS)
}

function removeSuppression() {
  docRoot().classList.remove(SUPPRESS_CLASS)
}

function isNonMousePointer(event) {
  return ['pen', 'touch'].includes(event?.pointerType || '')
}

function blurInteractiveElement() {
  const active = document.activeElement
  if (!(active instanceof HTMLElement)) return
  if (!active.matches(interactiveSelector)) return
  active.blur()
}

function handlePointerEnd(event) {
  if (!isNonMousePointer(event)) return
  lastPointerType = event.pointerType || lastPointerType
  addSuppression()
  blurInteractiveElement()
}

export function installPointerHoverGuard() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  if (window.__plantPointerHoverGuardInstalled) return
  window.__plantPointerHoverGuardInstalled = true

  document.addEventListener('pointerover', event => {
    if (event.pointerType === 'mouse' || event.pointerType === 'pen') {
      lastPointerType = event.pointerType
      removeSuppression()
    }
  }, true)

  document.addEventListener('pointermove', event => {
    if (event.pointerType === 'mouse' || event.pointerType === 'pen') {
      lastPointerType = event.pointerType
      removeSuppression()
    }
  }, true)

  document.addEventListener('pointerout', event => {
    if (event.pointerType === 'pen' && !event.relatedTarget) {
      lastPointerType = 'pen'
      addSuppression()
    }
  }, true)

  document.addEventListener('pointerleave', event => {
    if (!isNonMousePointer(event)) return
    lastPointerType = event.pointerType || lastPointerType
    addSuppression()
  }, true)

  document.addEventListener('pointerup', handlePointerEnd, true)
  document.addEventListener('pointercancel', handlePointerEnd, true)
  document.addEventListener('lostpointercapture', handlePointerEnd, true)

  document.addEventListener('touchend', () => {
    lastPointerType = 'touch'
    addSuppression()
    blurInteractiveElement()
  }, { capture: true, passive: true })

  document.addEventListener('touchcancel', () => {
    lastPointerType = 'touch'
    addSuppression()
    blurInteractiveElement()
  }, { capture: true, passive: true })

  window.addEventListener('blur', () => {
    if (lastPointerType !== 'mouse') {
      addSuppression()
      blurInteractiveElement()
    }
  })

  document.addEventListener('visibilitychange', () => {
    if (document.hidden && lastPointerType !== 'mouse') {
      addSuppression()
      blurInteractiveElement()
    }
  })
}
