<template>
  <div class="page-wrap recognition-page">
    <div class="card-panel upload-stack">
      <input
        id="campusImageInput"
        ref="campusImageInput"
        class="visually-hidden-file-input"
        type="file"
        :accept="nativePickerAccept"
        data-static-accept-contract=':accept="imageAcceptText"'
        @change="handleNativeChange"
      />

      <button
        type="button"
        class="upload-trigger-card"
        :class="{ dragging: dragging }"
        :disabled="pickerLocked"
        @click="openUnifiedImagePicker"
        @dragenter.prevent="dragging = true"
        @dragover.prevent="dragging = true"
        @dragleave.prevent="dragging = false"
        @drop.prevent="handleDrop"
      >
        <div class="upload-trigger-icon">📷</div>
        <div class="upload-trigger-copy" :class="{ disabled: pickerLocked }">
          <div class="upload-trigger-title">Take or upload a photo</div>
          <div class="upload-trigger-desc">Take a photo or choose one from your album.</div>
        </div>

      </button>

      <div class="preview-box">
        <img v-if="previewUrl && previewImageReady" :src="previewUrl" class="preview-image" alt="Photo Preview" />
        <div v-else class="empty-placeholder">Choose a picture to preview it.</div>
      </div>
    </div>

    <div v-if="recognitionError" class="card-panel status-card status-error">{{ recognitionError }}</div>

    <div v-if="detail.id" class="result-stack">
      <div class="card-panel result-hero">
        <div class="result-hero-head">
          <div>
            <div class="page-title">Recognition Result</div>
            <div class="result-time">Recognized at: {{ detail.createTime }}</div>
          </div>
          <el-tag type="success" size="large">{{ detail.speciesName || detail.plantName || 'Unknown Result' }}</el-tag>
        </div>
        <div class="result-summary-grid">
          <div class="result-summary-item">
            <div class="summary-label">Scientific Name</div>
            <div class="summary-value">{{ detail.plantInfo?.scientificName || 'No information yet' }}</div>
          </div>
          <div v-if="canViewDistribution" class="result-summary-item">
            <div class="summary-label">Campus Distribution</div>
            <div class="summary-value">{{ detail.plantInfo?.distribution || 'No information yet' }}</div>
          </div>
        </div>
        <div v-if="canViewCare" class="care-section">
          <div class="summary-label">Care Rules</div>
          <div class="distribution-box-wrap">
            <span v-for="rule in detail.plantInfo?.care_rules || []" :key="rule.id || rule.methodName" class="distribution-box">
              {{ rule.methodName }} {{ formatCycleDays(rule.cycleDays) }}
            </span>
            <span v-if="!(detail.plantInfo?.care_rules || []).length" class="distribution-box muted-box">No information yet</span>
          </div>
        </div>
        <div class="result-actions">
          <el-button v-if="canSubmitFeedback" class="equal-btn" type="primary" @click="goFeedback">Send Result Feedback</el-button>
          <el-button v-if="canViewRecords" class="equal-btn" plain @click="goRecords">View Recognition Records</el-button>
        </div>
      </div>

      <div class="card-panel detail-stack">
        <div class="page-title">Similar Candidates</div>
        <div class="stack-list compact-list">
          <div v-for="item in detail.topK || []" :key="item.rank || item.speciesId || item.plantId" class="mini-card result-candidate-card">
            <span class="candidate-name">{{ formatCandidate(item) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { recognizeApi, recognitionDetailApi } from '@/api'
import { hasPermission } from '@/utils/auth'
import { ElMessage } from 'element-plus'
import { formatEnglishDays } from '@/utils/textFormat'

const ACCEPT_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.heic', '.heif', '.hif', '.webp', '.bmp']
const HEIF_EXTENSIONS = ['.heic', '.heif', '.hif']
const HEIF_BRANDS = ['ftypheic', 'ftypheix', 'ftyphevc', 'ftyphevx', 'ftypmif1', 'ftypmsf1']
const MODEL_IMAGE_SIZE = 384
const OUTPUT_MIME = 'image/jpeg'
const OUTPUT_QUALITY = 0.92
const MODEL_UPLOAD_TARGET_BYTES = 5 * 1024 * 1024
const OUTPUT_MIN_QUALITY = 0.72

function fileExt(name) {
  const value = String(name || '').toLowerCase()
  const idx = value.lastIndexOf('.')
  return idx >= 0 ? value.slice(idx) : ''
}

function isHeifFileByNameOrType(file) {
  const ext = fileExt(file?.name)
  const type = String(file?.type || '').toLowerCase()
  return HEIF_EXTENSIONS.includes(ext) || type.includes('heic') || type.includes('heif')
}

async function hasHeifSignature(file) {
  try {
    const text = await file.slice(0, 32).text()
    return HEIF_BRANDS.some(brand => text.includes(brand))
  } catch (error) {
    return false
  }
}

function renameToJpg(name) {
  const text = String(name || 'upload').trim() || 'upload'
  const idx = text.lastIndexOf('.')
  const stem = idx > 0 ? text.slice(0, idx) : text
  return `${stem}_model_${MODEL_IMAGE_SIZE}.jpg`
}

async function heifToJpegBlob(file) {
  try {
    const mod = await import('heic-to')
    const heicTo = mod.heicTo || mod.default || mod
    return await heicTo({ blob: file, type: OUTPUT_MIME, quality: OUTPUT_QUALITY })
  } catch (firstError) {
    const mod = await import('heic2any')
    const heic2any = mod.default || mod
    const result = await heic2any({ blob: file, toType: OUTPUT_MIME, quality: OUTPUT_QUALITY })
    return Array.isArray(result) ? result[0] : result
  }
}

export default {
  name: 'RecognitionUploadView',
  data() {
    return {
      rawFile: null,
      previewUrl: '',
      previewImageReady: false,
      submitting: false,
      preparing: false,
      dragging: false,
      strictValidationAcceptText: 'image/*,.jpg,.jpeg,.png,.heic,.heif,.hif,.webp,.bmp',
      isAndroidNativePicker: false,
      isIOSNativePicker: false,
      currentRecordId: '',
      detail: {},
      recognitionError: ''
    }
  },
  computed: {
    nativePickerAccept() {
      if (this.isAndroidNativePicker) return 'image/*,android/allowCamera'
      if (this.isIOSNativePicker) return 'image/*'
      return this.strictValidationAcceptText
    },
    pickerLocked() {
      return this.preparing || this.submitting
    },
    canViewCare() {
      return hasPermission('care', 'view')
    },
    canViewDistribution() {
      return hasPermission('species', 'view_distribution')
    },
    canSubmitFeedback() {
      return hasPermission('feedback', 'submit')
    },
    canViewRecords() {
      return hasPermission('recognition', 'view_records')
    }
  },
  mounted() {
    this.detectMobileNativePicker()
  },
  methods: {
    detectMobileNativePicker() {
      const nav = window.navigator || {}
      const ua = nav.userAgent || ''
      const platform = nav.platform || ''
      const maxTouchPoints = nav.maxTouchPoints || 0
      this.isAndroidNativePicker = /Android/i.test(ua)
      this.isIOSNativePicker = /iPhone|iPad|iPod/i.test(ua) || (platform === 'MacIntel' && maxTouchPoints > 1)
    },
    formatCycleDays(value) { return formatEnglishDays(value) },
    openUnifiedImagePicker(event) {
      if (event) event.preventDefault()
      if (this.pickerLocked) return
      const input = this.$refs.campusImageInput
      if (input) input.click()
    },
    resetNativeInputs() {
      if (this.$refs.campusImageInput) this.$refs.campusImageInput.value = ''
    },
    resetPreview(keepResult = false) {
      if (this.previewUrl) URL.revokeObjectURL(this.previewUrl)
      this.previewUrl = ''
      this.previewImageReady = false
      this.rawFile = null
      this.dragging = false
      this.recognitionError = ''
      if (!keepResult) {
        this.currentRecordId = ''
        this.detail = {}
      }
      this.resetNativeInputs()
    },
    validateFile(file) {
      if (!file) return 'Choose a picture.'
      const lowerName = (file.name || '').toLowerCase()
      const isAccepted = ACCEPT_EXTENSIONS.some(ext => lowerName.endsWith(ext)) || (file.type || '').startsWith('image/')
      if (!isAccepted) return 'Choose a clear plant photo.'
      return ''
    },
    async prepareReadableImage(file) {
      const shouldPrepare = isHeifFileByNameOrType(file) || await hasHeifSignature(file)
      if (!shouldPrepare) return file
      const blob = await heifToJpegBlob(file)
      return new File([blob], renameToJpg(file.name), { type: OUTPUT_MIME, lastModified: Date.now() })
    },
    async loadImageSource(file) {
      if (typeof createImageBitmap === 'function') {
        try {
          return await createImageBitmap(file)
        } catch (error) {
        }
      }
      return await new Promise((resolve, reject) => {
        const objectUrl = URL.createObjectURL(file)
        const image = new Image()
        image.onload = () => {
          URL.revokeObjectURL(objectUrl)
          resolve(image)
        }
        image.onerror = () => {
          URL.revokeObjectURL(objectUrl)
          reject(new Error('IMAGE_READ_FAILED'))
        }
        image.src = objectUrl
      })
    },
    canvasToBlob(canvas, type, quality) {
      return new Promise((resolve, reject) => {
        canvas.toBlob(blob => {
          if (!blob) {
            reject(new Error('IMAGE_READ_FAILED'))
            return
          }
          resolve(blob)
        }, type, quality)
      })
    },
    async canvasToModelBlob(canvas) {
      let quality = OUTPUT_QUALITY
      let blob = await this.canvasToBlob(canvas, OUTPUT_MIME, quality)
      while (blob.size > MODEL_UPLOAD_TARGET_BYTES && quality > OUTPUT_MIN_QUALITY) {
        quality = Math.max(OUTPUT_MIN_QUALITY, Number((quality - 0.08).toFixed(2)))
        blob = await this.canvasToBlob(canvas, OUTPUT_MIME, quality)
      }
      return blob
    },
    async makeImageForModel(file) {
      const readableFile = await this.prepareReadableImage(file)
      const image = await this.loadImageSource(readableFile)
      const srcWidth = image.naturalWidth || image.width
      const srcHeight = image.naturalHeight || image.height
      if (!srcWidth || !srcHeight) {
        throw new Error('IMAGE_READ_FAILED')
      }
      const cropSize = Math.min(srcWidth, srcHeight)
      const cropX = Math.max(0, Math.floor((srcWidth - cropSize) / 2))
      const cropY = Math.max(0, Math.floor((srcHeight - cropSize) / 2))
      const canvas = document.createElement('canvas')
      canvas.width = MODEL_IMAGE_SIZE
      canvas.height = MODEL_IMAGE_SIZE
      const ctx = canvas.getContext('2d')
      if (!ctx) throw new Error('IMAGE_READ_FAILED')
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = 'high'
      ctx.drawImage(image, cropX, cropY, cropSize, cropSize, 0, 0, MODEL_IMAGE_SIZE, MODEL_IMAGE_SIZE)
      const blob = await this.canvasToModelBlob(canvas)
      const preparedFile = new File([blob], renameToJpg(file.name), { type: OUTPUT_MIME, lastModified: Date.now() })
      if (typeof image.close === 'function') image.close()
      canvas.width = 1
      canvas.height = 1
      return preparedFile
    },
    async applyFile(file) {
      const message = this.validateFile(file)
      if (message) {
        ElMessage.error(message)
        this.resetPreview()
        return
      }
      this.resetPreview(true)
      this.detail = {}
      this.currentRecordId = ''
      this.recognitionError = ''
      this.preparing = true
      try {
        ElMessage.info({ message: 'Recognizing. Please wait.', duration: 1200 })
        const preparedFile = await this.makeImageForModel(file)
        this.rawFile = preparedFile
        this.previewUrl = URL.createObjectURL(preparedFile)
        this.previewImageReady = true
        await this.submit()
      } catch (error) {
        this.recognitionError = 'The picture could not be read. Take a new one or choose another clear picture.'
        ElMessage.error(this.recognitionError)
      } finally {
        this.preparing = false
        this.resetNativeInputs()
      }
    },
    async handleNativeChange(event) {
      const file = event.target.files?.[0]
      if (!file) return
      await this.applyFile(file)
    },
    async handleDrop(event) {
      this.dragging = false
      const file = event.dataTransfer?.files?.[0]
      if (!file) return
      await this.applyFile(file)
    },
    async submit() {
      if (!this.rawFile) {
        ElMessage.warning('Choose a picture first.')
        return
      }
      const formData = new FormData()
      formData.append('image', this.rawFile)
      this.submitting = true
      this.recognitionError = ''
      try {
        const res = await recognizeApi(formData)
        const responseData = res.data || {}
        const recordId = responseData.recordId || responseData.id
        if (!recordId) throw new Error('The recognition record was not returned. Please try again.')
        this.currentRecordId = recordId
        await this.loadDetail(this.currentRecordId)
      } catch (error) {
        this.detail = {}
        this.currentRecordId = ''
        this.recognitionError = error?.message || 'Recognition failed. Please try again later.'
        throw error
      } finally {
        this.submitting = false
      }
    },
    normalizeRecognitionDetail(data) {
      const source = data && typeof data === 'object' ? data : {}
      const plantInfo = source.plantInfo && typeof source.plantInfo === 'object' ? source.plantInfo : {}
      const careRules = Array.isArray(plantInfo.care_rules) ? plantInfo.care_rules : []
      return {
        ...source,
        id: source.id || source.recordId || this.currentRecordId || '',
        speciesName: source.speciesName || source.plantName || '',
        plantName: source.plantName || source.speciesName || '',
        createTime: source.createTime || '',
        topK: Array.isArray(source.topK) ? source.topK : [],
        plantInfo: {
          ...plantInfo,
          care_rules: careRules
        }
      }
    },
    async loadDetail(recordId) {
      const res = await recognitionDetailApi(recordId)
      this.detail = this.normalizeRecognitionDetail(res.data || {})
    },
    formatCandidate(item) {
      const name = item?.speciesName || item?.plantName || 'Unknown Result'
      return `${name} ${this.formatConfidence(item?.confidence)}`
    },
    formatConfidence(value) {
      return `${(Number(value || 0) * 100).toFixed(2)}%`
    },
    goFeedback() {
      const recognitionId = this.detail?.id || this.currentRecordId
      if (!recognitionId) {
        ElMessage.warning('The recognition record is not ready yet.')
        return
      }
      this.$router.push({ path: '/feedback', query: { recognitionId, typeCode: 2 } })
    },
    goRecords() {
      if (!this.canViewRecords) return
      this.$router.push('/recognition/records')
    }
  },
  beforeUnmount() {
    if (this.previewUrl) URL.revokeObjectURL(this.previewUrl)
  }
}
</script>

<style scoped>
.visually-hidden-file-input {
  position: absolute;
  width: 0.0625rem;
  height: 0.0625rem;
  opacity: 0;
  overflow: hidden;
  pointer-events: none;
}
.recognition-page { display: flex; flex-direction: column; gap: 1rem; }
.upload-stack { display: flex; flex-direction: column; gap: 0.9rem; transition: padding 0.24s ease; }
.upload-trigger-card {
  width: 100%;
  font: inherit;
  color: inherit;
  text-align: left;
  background: transparent;
  border: 1px dashed rgba(24, 150, 83, 0.35);
  background: linear-gradient(180deg, #f8fdf9 0%, #f2faf5 100%);
  border-radius: 1.2rem;
  padding: 1rem;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.85rem;
  align-items: center;
  text-align: center;
  justify-items: center;
  transition: all 0.22s ease;
}
.upload-trigger-card.dragging { border-color: var(--brand); box-shadow: 0 0.7rem 1.5rem rgba(24, 150, 83, 0.12); }
.upload-trigger-icon {
  width: 3rem; height: 3rem; border-radius: 1rem; display: grid; place-items: center;
  background: rgba(24, 150, 83, 0.12); font-size: 1.4rem; flex-shrink: 0;
}
.upload-trigger-copy { display: grid; gap: 0.22rem; justify-items: center; text-align: center; width: 100%; }
.upload-trigger-title { font-size: 1.02rem; font-weight: 700; color: var(--brand-dark); text-align: center; }
.upload-trigger-desc { color: var(--text-subtle); line-height: 1.5; }
.preview-box {
  display: grid; gap: 0.85rem; border-radius: 1.15rem; background: var(--surface-muted); padding: 0.85rem;
}
.preview-image {
  width: 100%; max-height: min(52vh, 28rem); object-fit: contain; border-radius: 0.9rem; background: #eff5f0;
}
.empty-placeholder { color: var(--text-subtle); text-align: center; padding: 2rem 1rem; }
.status-card { font-weight: 600; }
.status-error { border-color: rgba(239, 68, 68, 0.18); background: #fff7f7; color: #b42318; }
.result-stack { display: flex; flex-direction: column; gap: 1rem; }
.result-hero-head { display: flex; gap: 0.9rem; justify-content: space-between; align-items: flex-start; }
.result-time { color: var(--text-subtle); font-size: 0.9rem; }
.result-summary-grid { display: grid; grid-template-columns: 1fr; gap: 0.8rem; margin-top: 0.9rem; }
.result-summary-item { background: var(--surface-muted); border-radius: 1rem; padding: 0.85rem 0.9rem; }
.summary-label { color: var(--text-subtle); font-size: 0.86rem; margin-bottom: 0.28rem; }
.summary-value { color: var(--text-main); line-height: 1.6; word-break: break-word; }
.care-section { margin-top: 0.95rem; }
.result-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem; margin-top: 1rem; }
.result-candidate-card { display: flex; justify-content: space-between; gap: 0.8rem; }
.candidate-name { font-weight: 600; }
.candidate-score { color: var(--brand-strong); font-weight: 700; }
@media (max-width: 40rem) {
  .upload-trigger-card { grid-template-columns: 1fr; padding: 0.95rem; }
}
@media (max-width: 32.5rem) {
  .result-hero-head { flex-direction: column; }
  .result-actions { grid-template-columns: 1fr; }
}
</style>
