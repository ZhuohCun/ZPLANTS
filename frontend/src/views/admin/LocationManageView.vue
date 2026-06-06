<template>
  <div class="page-wrap location-page-panel">
    <div class="card-panel">
      <div class="section-head section-head-tight split-header">
        <div class="head-main-block">
          <div class="section-title">Zone Management</div>
        </div>
        <div class="head-action-block">
          <el-button v-if="canCreate" class="header-mini-btn" type="primary" @click="openZoneDialog()">Add Zone</el-button>
        </div>
      </div>
      <div v-if="zones.length" class="zone-stage-grid top-gap-small">
        <button v-for="item in zones" :key="item.id" class="zone-pick-card" :class="{ active: currentZone && currentZone.id === item.id }" @click="selectZone(item)">
          <div class="zone-card-title-row">
            <div>
              <div class="list-title">{{ item.zoneName }}</div>
              <div class="list-desc">Locations:{{ item.locationCount }}</div>
            </div>
          </div>
          <div class="mini-actions location-action-bar top-gap-small" :class="zoneActionClass()">
            <el-button class="equal-btn" type="success" plain @click.stop="openLocationPanel(item)">Manage Locations</el-button>
            <el-button v-if="canUpdate" class="equal-btn" plain @click.stop="openZoneDialog(item)">Edit Zone</el-button>
            <el-button v-if="canDelete" class="equal-btn" type="danger" plain @click.stop="deleteZone(item)">Delete Zone</el-button>
          </div>
        </button>
      </div>
      <div v-else class="empty-state">No information yet</div>
    </div>
    <el-dialog v-model="zoneDialog" :title="zoneForm.id ? 'Edit Zone' : 'Add Zone'" destroy-on-close>
      <el-form :model="zoneForm" label-position="top">
        <el-form-item label="Zone Name"><el-input v-model="zoneForm.zoneName" /></el-form-item>
      </el-form>
      <template #footer>
        <div class="dual-action">
          <el-button class="equal-btn" @click="zoneDialog = false">Cancel</el-button>
          <el-button class="equal-btn" type="primary" @click="saveZone">Save</el-button>
        </div>
      </template>
    </el-dialog>
    <el-dialog v-model="panelVisible" :title="currentZone ? `${currentZone.zoneName} · Location Management` : 'Location Management'" width="92%" destroy-on-close>
      <div v-if="currentZone">
        <div class="section-head section-head-tight split-header">
          <div class="head-main-block">
            <div class="section-title">{{ currentZone.zoneName }}</div>
          </div>
          <div class="head-action-block">
            <el-button v-if="canCreate" class="header-mini-btn" type="primary" @click="openLocation()">Add Location</el-button>
          </div>
        </div>
        <div v-if="locations.length" class="stack-list top-gap-small">
          <div v-for="item in locations" :key="item.id" class="mini-card mini-card-column">
            <div class="list-title-row wrap-row"><span class="list-title">{{ item.locationName }}</span></div>
            <div class="mini-actions top-gap-small" :class="locationActionClass()">
              <el-button v-if="canUpdate" class="equal-btn" type="primary" plain @click="openLocation(item)">Edit</el-button>
              <el-button v-if="canDelete" class="equal-btn" type="danger" plain @click="deleteLocation(item)">Delete</el-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-state top-gap-small">No information yet</div>
      </div>
      <template #footer>
        <div class="dual-action single-action-row"><el-button class="equal-btn" @click="panelVisible = false">Off</el-button></div>
      </template>
    </el-dialog>
    <el-dialog v-model="locationDialog" :title="locationForm.id ? 'Edit Location' : 'Add Location'" destroy-on-close>
      <el-form :model="locationForm" label-position="top">
        <el-form-item label="Zone"><el-input :model-value="currentZone ? currentZone.zoneName : ''" disabled /></el-form-item>
        <el-form-item label="Location Name"><el-input v-model="locationForm.locationName" /></el-form-item>
      </el-form>
      <template #footer>
        <div class="dual-action">
          <el-button class="equal-btn" @click="locationDialog = false">Cancel</el-button>
          <el-button class="equal-btn" type="primary" @click="saveLocation">Save</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>
<script>
import { zoneListApi, createZoneApi, updateZoneApi, deleteZoneApi, zoneLocationListApi, createZoneLocationApi, updateLocationApi, deleteLocationApi } from '@/api'
import { hasPermission } from '@/utils/auth'
import { ElMessageBox, ElMessage } from 'element-plus'
export default {
  computed: {
    canView() { return hasPermission('zone_location', 'view') },
    canCreate() { return hasPermission('zone_location', 'create') },
    canUpdate() { return hasPermission('zone_location', 'update') },
    canDelete() { return hasPermission('zone_location', 'delete') }
  },
  data() {
    return { zones: [], currentZone: null, locations: [], zoneDialog: false, locationDialog: false, panelVisible: false, zoneForm: { id: '', zoneName: '' }, locationForm: { id: '', locationName: '' } }
  },
  created() { if (!this.canView) return; this.loadZones() },
  methods: {
    zoneActionClass() { const count = 1 + (this.canUpdate ? 1 : 0) + (this.canDelete ? 1 : 0); return `action-count-${count}` },
    locationActionClass() { const count = (this.canUpdate ? 1 : 0) + (this.canDelete ? 1 : 0); return `action-count-${Math.max(1, count)}` },
    async loadZones() { if (!this.canView) { this.zones = []; return } this.zones = (await zoneListApi()).data || [] },
    async loadLocations(zoneId) { if (!this.canView) { this.locations = []; return } this.locations = (await zoneLocationListApi(zoneId)).data || [] },
    selectZone(item) { this.currentZone = item },
    async openLocationPanel(item) { this.currentZone = item; await this.loadLocations(item.id); this.panelVisible = true },
    openZoneDialog(item) { if (!this.canUpdate && item) return; if (!this.canCreate && !item) return; this.zoneForm = item ? { id: item.id, zoneName: item.zoneName } : { id: '', zoneName: '' }; this.zoneDialog = true },
    async saveZone() { if (!(this.zoneForm.zoneName || '').trim()) { ElMessage.warning('Enter a zone name.'); return } if (this.zoneForm.id) await updateZoneApi(this.zoneForm.id, this.zoneForm); else await createZoneApi(this.zoneForm); this.zoneDialog = false; await this.loadZones(); if (this.currentZone?.id) { const target = this.zones.find(item => item.id === this.currentZone.id); if (target) this.currentZone = target } },
    openLocation(item) { if (!this.currentZone) return; if (!this.canUpdate && item) return; if (!this.canCreate && !item) return; this.locationForm = item ? { id: item.id, locationName: item.locationName } : { id: '', locationName: '' }; this.locationDialog = true },
    async saveLocation() { if (!this.currentZone) return; if (!(this.locationForm.locationName || '').trim()) { ElMessage.warning('Enter a location name.'); return } if (this.locationForm.id) await updateLocationApi(this.locationForm.id, this.locationForm); else await createZoneLocationApi(this.currentZone.id, this.locationForm); this.locationDialog = false; await this.loadLocations(this.currentZone.id); await this.loadZones() },
    async deleteZone(item) {
      await ElMessageBox.confirm('Delete this zone?', 'Notice', { type: 'warning' })
      try {
        await deleteZoneApi(item.id)
        if (this.currentZone && Number(this.currentZone.id) === Number(item.id)) {
          this.currentZone = null
          this.locations = []
          this.panelVisible = false
        }
        await this.loadZones()
      } catch (error) {
        if (Number(error?.code) === 1404) {
          ElMessage.error('Remove all locations under this zone before deleting it.')
          return
        }
        throw error
      }
    },
    async deleteLocation(item) {
      await ElMessageBox.confirm('Delete this location?', 'Notice', { type: 'warning' })
      try {
        await deleteLocationApi(item.id)
        await this.loadLocations(this.currentZone.id)
        await this.loadZones()
      } catch (error) {
        if (Number(error?.code) === 1414) {
          ElMessage.error('Remove all plants under this location before deleting it.')
          return
        }
        throw error
      }
    }
  }
}
</script>
