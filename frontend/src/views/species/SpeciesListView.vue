<template>
  <div class="page-wrap">
    <template v-if="canView">
      <div class="card-panel">
        <div class="toolbar mobile-toolbar toolbar-with-actions">
          <el-input v-model="query.keyword" @keyup.enter="applySearch" @clear="applySearch" placeholder="Search species name or scientific name" clearable />
          <el-button class="equal-btn" type="success" @click="applySearch">Search</el-button>
          <el-button v-if="canCreate" class="equal-btn" type="primary" @click="openDialog()">Add Plant Species</el-button>
        </div>
        <div v-if="tableData.list?.length" class="stack-list top-gap-small">
          <div v-for="item in tableData.list" :key="item.id" class="list-card list-card-stacked species-list-card">
            <div class="list-card-body wide-body species-card-body">
              <div class="species-card-media">
                <img v-if="item.imageUrl" :src="assetUrl(item.imageUrl)" class="cover-image species-cover-image" @error="setImageFallback" />
                <div v-else class="species-cover-image species-cover-image-placeholder">No photo</div>
              </div>
              <div class="species-card-content">
              <div class="list-title-row wrap-row"><span class="list-title">{{ item.speciesName || 'Unnamed Species' }}</span><span class="list-time">{{ item.scientificName || 'No information yet' }}</span></div>
              <div v-if="canViewDistribution" class="list-desc">Locations</div>
              <div v-if="canViewDistribution" class="distribution-box-wrap top-gap-small">
                <span v-for="part in splitDistribution(item.distribution)" :key="`${item.id}-${part}`" class="distribution-box">{{ part }}</span>
                <span v-if="!splitDistribution(item.distribution).length" class="distribution-box muted-box">No information yet</span>
              </div>
              <div v-if="canViewCare" class="section-caption top-gap-small">Care Rules</div>
              <div v-if="canViewCare" class="distribution-box-wrap">
                <span v-for="rule in item.care_rules || []" :key="`${item.id}-${rule.id || rule.methodName}`" class="distribution-box">{{ rule.methodName }} {{ formatCycleDays(rule.cycleDays) }}</span>
                <span v-if="!(item.care_rules || []).length" class="distribution-box muted-box">No information yet</span>
              </div>
              <div class="mini-actions top-gap-small" :class="actionClass()">
                <el-button class="equal-btn" type="success" plain @click="goDetail(item.id)">View Details</el-button>
                <el-button v-if="canUpdate" class="equal-btn" type="primary" plain @click="openDialog(item)">Edit</el-button>
                <el-button v-if="canDelete" class="equal-btn" type="danger" plain @click="remove(item)">Delete</el-button>
              </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">No information yet</div>
        <div v-if="(tableData.total || 0) > (query.pageSize || 5)" class="pager-wrap"><el-pagination background layout="prev, pager, next" :current-page="query.pageNum" :page-size="query.pageSize" :total="tableData.total || 0" @current-change="changePage" /></div>
      </div>
      <el-dialog v-model="dialogVisible" :title="form.id ? 'Edit Plant Species' : 'Add Plant Species'" destroy-on-close>
        <el-form :model="form" label-position="top">
          <div class="form-grid mobile-form-grid fixed-two-grid">
            <el-form-item label="Species Name"><el-input v-model="form.speciesName" /></el-form-item>
            <el-form-item label="Scientific Name"><el-input v-model="form.scientificName" /></el-form-item>
          </div>
          <el-form-item label="Light Needs" class="full-span-item"><el-input v-model="form.lightRequirement" /></el-form-item>
          <el-form-item label="Care Notes"><el-input v-model="form.carePoints" type="textarea" :rows="3" /></el-form-item>
          <div class="section-caption">Care Rules</div>
          <div class="stack-list top-gap-small">
            <div v-for="(rule, index) in form.care_rules" :key="`rule-${index}`" class="mini-card mini-card-column align-left-btn rule-card" :class="{ active: expandedRuleIndex === index }">
              <button type="button" class="rule-card-toggle" @click="toggleRule(index)">
                <div class="list-title-row wrap-row"><span class="list-title">{{ careMethodName(rule.careMethodId) || 'Unnamed Rule' }}</span><span class="list-time">{{ formatCycleDays(rule.cycleDays) }}</span></div>
                <div class="rule-card-hint">Expand or collapse this rule</div>
              </button>
              <div v-if="expandedRuleIndex === index" class="rule-editor top-gap-small">
                <div class="form-grid mobile-form-grid fixed-two-grid">
                  <el-form-item label="Rule Name"><el-select v-model="rule.careMethodId" placeholder="Choose a care method" style="width:100%"><el-option v-for="item in care_methods" :key="item.id" :label="item.methodName" :value="item.id" /></el-select></el-form-item>
                  <el-form-item label="Reminder Cycle (days)"><el-input v-model="rule.cycleDays" type="number" min="1" step="1" inputmode="numeric" placeholder="Enter a positive whole number of days" /></el-form-item>
                </div>
                <div class="single-action-bar top-gap-small"><el-button class="equal-btn" type="danger" plain @click="removeRule(index)">Delete</el-button></div>
              </div>
            </div>
            <div v-if="!form.care_rules.length && !newRuleVisible" class="empty-state in-card-empty">No rules yet</div>
            <div v-if="newRuleVisible" class="mini-card mini-card-column rule-card active">
              <div class="list-title-row wrap-row"><span class="list-title">Add Rule</span><span class="list-time">Complete the rule information.</span></div>
              <div class="rule-editor top-gap-small">
                <div class="form-grid mobile-form-grid fixed-two-grid">
                  <el-form-item label="Rule Name"><el-select v-model="newRuleDraft.careMethodId" placeholder="Choose a care method" style="width:100%"><el-option v-for="item in care_methods" :key="item.id" :label="item.methodName" :value="item.id" /></el-select></el-form-item>
                  <el-form-item label="Reminder Cycle (days)"><el-input v-model="newRuleDraft.cycleDays" type="number" min="1" step="1" inputmode="numeric" placeholder="Enter a positive whole number of days" /></el-form-item>
                </div>
                <div class="dual-action spaced-action"><el-button class="equal-btn" type="primary" @click="confirmNewRule">Add Rule</el-button><el-button class="equal-btn" plain @click="cancelNewRule">Cancel</el-button></div>
              </div>
            </div>
          </div>
          <div class="single-action-bar top-gap-small"><el-button class="equal-btn" type="success" plain @click="startCreateRule">Add Rule</el-button></div>
          <el-form-item label="Species Photo" class="top-gap-small">
            <input ref="speciesFileInput" class="hidden-file-input" type="file" accept="image/*,.jpg,.jpeg,.png,.heic,.heif,.hif,.webp,.bmp" @change="handleNativeFile" />
            <button class="upload-trigger-card upload-trigger-card-small" type="button" @click="$refs.speciesFileInput.click()">
              <div class="upload-trigger-title">Take or upload a photo</div>
            </button>
            <div class="species-preview-wrap top-gap-small"><img v-if="imagePreview" :src="assetUrl(imagePreview)" class="cover-image species-cover-image species-cover-image-preview" @error="setImageFallback" /></div>
          </el-form-item>
        </el-form>
        <template #footer><div class="dialog-footer dual-action spaced-action"><el-button class="equal-btn" @click="dialogVisible = false">Cancel</el-button><el-button class="equal-btn" type="primary" @click="submit">Save</el-button></div></template>
      </el-dialog>
    </template>
    <div v-else class="card-panel view-empty-card"><div class="empty-state">No information yet</div></div>
  </div>
</template>
<script>
import { speciesListApi, createSpeciesApi, updateSpeciesApi, deleteSpeciesApi, speciesDetailApi, careMethodListApi } from '@/api'
import { hasPermission } from '@/utils/auth'
import { backendAssetUrl, DEFAULT_COVER_URL } from '@/api/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatEnglishDays } from '@/utils/textFormat'

const SPECIES_IMAGE_MAX_EDGE = 1600
const SPECIES_IMAGE_TARGET_BYTES = 2.5 * 1024 * 1024
const SPECIES_IMAGE_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
const SPECIES_IMAGE_MIME = 'image/jpeg'
const SPECIES_IMAGE_INITIAL_QUALITY = 0.92
const SPECIES_IMAGE_MIN_QUALITY = 0.68
const SPECIES_HEIF_EXTENSIONS = ['.heic', '.heif', '.hif']
const SPECIES_HEIF_BRANDS = ['ftypheic', 'ftypheix', 'ftyphevc', 'ftyphevx', 'ftypmif1', 'ftypmsf1']
const SPECIES_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.heic', '.heif', '.hif', '.webp', '.bmp']


function speciesFileExt(name) {
  const value = String(name || '').toLowerCase()
  const index = value.lastIndexOf('.')
  return index >= 0 ? value.slice(index) : ''
}

function isSpeciesHeifFile(file) {
  const ext = speciesFileExt(file?.name)
  const type = String(file?.type || '').toLowerCase()
  return SPECIES_HEIF_EXTENSIONS.includes(ext) || type.includes('heic') || type.includes('heif')
}

async function hasSpeciesHeifSignature(file) {
  try {
    const text = await file.slice(0, 32).text()
    return SPECIES_HEIF_BRANDS.some(brand => text.includes(brand))
  } catch (error) {
    return false
  }
}

async function convertSpeciesHeifToJpeg(file) {
  try {
    const mod = await import('heic-to')
    const heicTo = mod.heicTo || mod.default || mod
    return await heicTo({ blob: file, type: SPECIES_IMAGE_MIME, quality: SPECIES_IMAGE_INITIAL_QUALITY })
  } catch (firstError) {
    const mod = await import('heic2any')
    const heic2any = mod.default || mod
    const result = await heic2any({ blob: file, toType: SPECIES_IMAGE_MIME, quality: SPECIES_IMAGE_INITIAL_QUALITY })
    return Array.isArray(result) ? result[0] : result
  }
}

function validateSpeciesImageFile(file) {
  if (!file) return 'NO_FILE'
  if (file.size > SPECIES_IMAGE_MAX_UPLOAD_BYTES) return 'TOO_LARGE'
  const ext = speciesFileExt(file.name)
  if (SPECIES_IMAGE_EXTENSIONS.includes(ext) || String(file.type || '').startsWith('image/')) return ''
  return 'NOT_IMAGE'
}

function renameSpeciesImageToJpg(name) {
  const text = String(name || 'species-image').trim() || 'species-image'
  const dotIndex = text.lastIndexOf('.')
  const stem = dotIndex > 0 ? text.slice(0, dotIndex) : text
  return `${stem}_species.jpg`
}

export default {
  data() {
    return { query: { keyword: '', pageNum: 1, pageSize: 5 }, tableData: { list: [], total: 0 }, dialogVisible: false, care_methods: [], form: { care_rules: [] }, expandedRuleIndex: null, newRuleVisible: false, newRuleDraft: { careMethodId: '', cycleDays: '' }, imageFile: null, imagePreview: '' }
  },
  computed: {
    canView() { return hasPermission('species', 'view') },
    canViewDistribution() { return hasPermission('species', 'view_distribution') },
    canViewCare() { return hasPermission('care', 'view') },
    canCreate() { return hasPermission('species', 'create') },
    canUpdate() { return hasPermission('species', 'update') },
    canDelete() { return hasPermission('species', 'delete') }
  },
  created() { if (!this.canView) return; this.loadData(); this.loadCareMethods() },
  methods: {
    formatCycleDays(value) { return formatEnglishDays(value) },
    setImageFallback(event) { event.target.src = DEFAULT_COVER_URL },
    assetUrl(value) { return backendAssetUrl(value) },
    splitDistribution(text) { return (text || '').split(', ').map(item => item.trim()).filter(Boolean) },
    careMethodName(id) { return (this.care_methods.find(item => Number(item.id) === Number(id)) || {}).methodName || '' },
    actionClass() { const count = 1 + (this.canUpdate ? 1 : 0) + (this.canDelete ? 1 : 0); return `action-count-${count}` },
    async loadCareMethods() { if (!this.canView) { this.care_methods = []; return } const res = await careMethodListApi({ pageNum: 1, pageSize: 999, silentView: 1 }); this.care_methods = res.data?.list || [] },
    async loadData() { if (!this.canView) { this.tableData = { list: [], total: 0 }; return } const res = await speciesListApi(this.query); this.tableData = res.data || { list: [], total: 0 } },
    applySearch() { this.query.pageNum = 1; this.loadData() },
    changePage(page) { this.query.pageNum = page; this.loadData() },
    goDetail(id) { this.$router.push(`/species/${id}`) },
    async prepareSpeciesReadableImage(file) {
      const shouldConvert = isSpeciesHeifFile(file) || await hasSpeciesHeifSignature(file)
      if (!shouldConvert) return file
      const blob = await convertSpeciesHeifToJpeg(file)
      return new File([blob], renameSpeciesImageToJpg(file.name), { type: SPECIES_IMAGE_MIME, lastModified: Date.now() })
    },
    async loadImageForSpecies(file) {
      if (window.createImageBitmap) {
        try {
          return await window.createImageBitmap(file, { imageOrientation: 'from-image' })
        } catch (error) {

        }
      }
      const objectUrl = URL.createObjectURL(file)
      try {
        return await new Promise((resolve, reject) => {
          const image = new Image()
          image.onload = () => resolve(image)
          image.onerror = () => reject(new Error('IMAGE_DECODE_FAILED'))
          image.src = objectUrl
        })
      } finally {
        URL.revokeObjectURL(objectUrl)
      }
    },
    async canvasToBlob(canvas, quality) {
      return await new Promise((resolve, reject) => {
        canvas.toBlob(blob => {
          if (blob) resolve(blob)
          else reject(new Error('IMAGE_CONVERT_FAILED'))
        }, SPECIES_IMAGE_MIME, quality)
      })
    },
    async convertSpeciesImageForUpload(file) {
      const readableFile = await this.prepareSpeciesReadableImage(file)
      const image = await this.loadImageForSpecies(readableFile)
      const srcWidth = image.naturalWidth || image.width
      const srcHeight = image.naturalHeight || image.height
      if (!srcWidth || !srcHeight) throw new Error('IMAGE_SIZE_INVALID')
      const scale = Math.min(1, SPECIES_IMAGE_MAX_EDGE / Math.max(srcWidth, srcHeight))
      const targetWidth = Math.max(1, Math.round(srcWidth * scale))
      const targetHeight = Math.max(1, Math.round(srcHeight * scale))
      const canvas = document.createElement('canvas')
      canvas.width = targetWidth
      canvas.height = targetHeight
      const ctx = canvas.getContext('2d', { alpha: false })
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, targetWidth, targetHeight)
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = 'high'
      ctx.drawImage(image, 0, 0, targetWidth, targetHeight)
      if (typeof image.close === 'function') image.close()
      let quality = SPECIES_IMAGE_INITIAL_QUALITY
      let blob = await this.canvasToBlob(canvas, quality)
      while (blob.size > SPECIES_IMAGE_TARGET_BYTES && quality > SPECIES_IMAGE_MIN_QUALITY) {
        quality = Math.max(SPECIES_IMAGE_MIN_QUALITY, Number((quality - 0.08).toFixed(2)))
        blob = await this.canvasToBlob(canvas, quality)
      }
      return new File([blob], renameSpeciesImageToJpg(file.name), { type: SPECIES_IMAGE_MIME, lastModified: Date.now() })
    },
    async handleNativeFile(event) {
      const file = event.target.files?.[0]
      if (!file) return
      const invalid = validateSpeciesImageFile(file)
      if (invalid) {
        ElMessage.error(invalid === 'TOO_LARGE' ? 'Images must be 5MB or smaller.' : 'Please choose a clear image file.')
        if (this.$refs.speciesFileInput) this.$refs.speciesFileInput.value = ''
        return
      }
      try {
        const convertedFile = await this.convertSpeciesImageForUpload(file)
        this.imageFile = convertedFile
        if (this.imagePreview && this.imagePreview.startsWith('blob:')) URL.revokeObjectURL(this.imagePreview)
        this.imagePreview = URL.createObjectURL(convertedFile)
      } catch (error) {
        ElMessage.error('This picture cannot be read. Choose another clear picture.')
        this.imageFile = null
        if (this.$refs.speciesFileInput) this.$refs.speciesFileInput.value = ''
      }
    },
    toggleRule(index) { this.newRuleVisible = false; this.expandedRuleIndex = this.expandedRuleIndex === index ? null : index },
    startCreateRule() { this.expandedRuleIndex = null; this.newRuleVisible = true; this.newRuleDraft = { careMethodId: '', cycleDays: '' } },
    cancelNewRule() { this.newRuleVisible = false; this.newRuleDraft = { careMethodId: '', cycleDays: '' } },
    validateRule(rule) { if (!rule.careMethodId) return 'Choose a care method'; const value = String(rule.cycleDays || '').trim(); if (!/^\d+$/.test(value) || Number(value) <= 0) return 'The reminder cycle must be a positive whole number of days.'; return '' },
    hasDuplicateRule(rule, excludedIndex = -1) { return (this.form.care_rules || []).some((item, index) => index !== excludedIndex && Number(item.careMethodId) === Number(rule.careMethodId)) },
    confirmNewRule() {
      const message = this.validateRule(this.newRuleDraft)
      if (message) { ElMessage.warning(message); return }
      if (this.hasDuplicateRule(this.newRuleDraft)) { ElMessage.error('The same care rule already exists.'); return }
      this.form.care_rules.push({ careMethodId: Number(this.newRuleDraft.careMethodId), cycleDays: String(Math.trunc(Number(this.newRuleDraft.cycleDays))) })
      this.cancelNewRule()
    },
    removeRule(index) { this.form.care_rules.splice(index, 1); if (this.expandedRuleIndex === index) this.expandedRuleIndex = null; if (this.expandedRuleIndex !== null && this.expandedRuleIndex > index) this.expandedRuleIndex -= 1 },
    async openDialog(item) {
      this.expandedRuleIndex = null
      this.cancelNewRule()
      this.imageFile = null
      if (this.imagePreview && this.imagePreview.startsWith('blob:')) { URL.revokeObjectURL(this.imagePreview) }
      if (item?.id) {
        const res = await speciesDetailApi(item.id)
        const detail = res.data || {}
        this.form = { id: detail.id, speciesName: detail.speciesName || '', scientificName: detail.scientificName || '', lightRequirement: detail.lightRequirement || '', carePoints: detail.carePoints || '', care_rules: (detail.care_rules || []).map(rule => ({ careMethodId: rule.careMethodId, cycleDays: String(rule.cycleDays || '') })) }
        this.imagePreview = detail.imageUrl || ''
      } else {
        this.form = { speciesName: '', scientificName: '', lightRequirement: '', carePoints: '', care_rules: [] }
        this.imagePreview = ''
      }
      this.dialogVisible = true
    },
    async submit() {
      if (!(this.form.speciesName || '').trim()) { ElMessage.warning('Enter the species name.'); return }
      if (this.newRuleVisible) { ElMessage.warning('Save or cancel the current new rule first.'); return }
      const seenMethodIds = new Set()
      for (const rule of this.form.care_rules || []) {
        const message = this.validateRule(rule)
        if (message) { ElMessage.warning(message); return }
        const methodId = Number(rule.careMethodId)
        if (seenMethodIds.has(methodId)) { ElMessage.error('The same care rule already exists.'); return }
        seenMethodIds.add(methodId)
      }
      const fd = new FormData()
      fd.append('speciesName', this.form.speciesName || '')
      fd.append('scientificName', this.form.scientificName || '')
      fd.append('lightRequirement', this.form.lightRequirement || '')
      fd.append('carePoints', this.form.carePoints || '')
      fd.append('care_rules', JSON.stringify((this.form.care_rules || []).filter(item => item.careMethodId && item.cycleDays).map(item => ({ careMethodId: Number(item.careMethodId), cycleDays: String(item.cycleDays) }))))
      if (this.imageFile) fd.append('speciesImage', this.imageFile)
      if (this.form.id) await updateSpeciesApi(this.form.id, fd)
      else await createSpeciesApi(fd)
      this.dialogVisible = false
      this.loadData()
    },
    async remove(item) { if (Number(item.plantCount || 0) > 0) { ElMessage.warning('This species still has plants. Remove those records before deleting the species.'); return } await ElMessageBox.confirm(`Delete plant species "${item.speciesName}"?`, 'Notice', { type: 'warning' }); await deleteSpeciesApi(item.id); this.loadData() }
  },
  beforeUnmount() { if (this.imagePreview && this.imagePreview.startsWith('blob:')) URL.revokeObjectURL(this.imagePreview) }
}
</script>


<style scoped>
.species-list-card { overflow: hidden; }
.species-card-body { display: grid; grid-template-columns: clamp(9.6rem, 24vw, 11.8rem) minmax(0, 1fr); gap: 1rem; align-items: stretch; }
.species-card-media { display: flex; align-items: center; justify-content: center; width: 100%; min-width: 0; }
.species-preview-wrap { display: flex; justify-content: center; align-items: center; width: 100%; min-height: 8.4rem; }
.full-span-item { width: 100%; }
.species-cover-image { width: 100%; aspect-ratio: 5 / 3; object-fit: cover; object-position: center center; border-radius: 0.95rem; background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%); box-shadow: 0 0.45rem 1.2rem rgba(15, 23, 42, 0.08); max-height: 7.1rem; }
.species-cover-image-preview { width: min(100%, 18rem); aspect-ratio: 5 / 3; object-fit: cover; object-position: center center; border-radius: 0.95rem; background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%); box-shadow: 0 0.45rem 1.2rem rgba(15, 23, 42, 0.08); max-height: 7.1rem; margin: 0 auto; }
.species-cover-image-placeholder { display: flex; align-items: center; justify-content: center; color: #94a3b8; font-size: 0.82rem; }
.species-card-content { min-width: 0; display: flex; flex-direction: column; justify-content: center; gap: 0.28rem; }
@media (max-width: 640px) {
  .species-card-body { grid-template-columns: 1fr; gap: 0.8rem; justify-items: center; }
  .species-card-media { width: 100%; max-width: min(100%, 20rem); margin: 0 auto; align-items: center; justify-content: center; }
  .species-cover-image { width: min(100%, 20rem); max-height: none; margin: 0 auto; }
  .species-card-content { width: 100%; align-self: stretch; }
}
@media (max-width: 640px) and (orientation: portrait) {
  .species-card-media { max-width: min(100%, 21rem); }
  .species-cover-image { width: min(100%, 21rem); }
}
</style>
