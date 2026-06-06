import { request } from './request'
import {
  encryptedLoginPayload,
  encryptedProfilePasswordPayload,
  encryptedRegisterPayload,
  encryptedUserPayload,
  hashPasswordText
} from '@/utils/passwordCrypto'

export const loginApi = async (data) => request({ url: '/auth/login', method: 'post', data: await encryptedLoginPayload(data) })
export const registerApi = async (data) => request({ url: '/auth/register', method: 'post', data: await encryptedRegisterPayload(data) })
export const profileApi = () => request({ url: '/auth/profile/detail', method: 'get' })
export const updateProfileApi = (data) => request({ url: '/auth/profile/update', method: 'put', data })
export const updatePasswordApi = async (data) => request({ url: '/auth/password', method: 'put', data: await encryptedProfilePasswordPayload(data) })
export const logoutApi = () => request({ url: '/auth/logout', method: 'post' })

export const dashboardApi = () => request({ url: '/dashboard/summary', method: 'get' })

export const recognizeApi = (data) => request({ url: '/recognitions/create', method: 'post', data })
export const recognitionListApi = (params) => request({ url: '/recognitions/list', method: 'get', params })
export const recognitionDetailApi = (id) => request({ url: `/recognitions/detail/${id}`, method: 'get' })
export const recognitionOptionsApi = (params) => request({ url: '/recognitions/options', method: 'get', params })

export const speciesListApi = (params) => request({ url: '/species/list', method: 'get', params })
export const speciesDetailApi = (id) => request({ url: `/species/detail/${id}`, method: 'get' })
export const createSpeciesApi = (data) => request({ url: '/species/create', method: 'post', data })
export const updateSpeciesApi = (id, data) => request({ url: `/species/update/${id}`, method: 'put', data })
export const deleteSpeciesApi = (id) => request({ url: `/species/delete/${id}`, method: 'delete' })

export const plantListApi = (params) => request({ url: '/plants/list', method: 'get', params })
export const plantDetailApi = (id) => request({ url: `/plants/detail/${id}`, method: 'get' })
export const createPlantApi = (data) => request({ url: '/plants/create', method: 'post', data })
export const updatePlantApi = (id, data) => request({ url: `/plants/update/${id}`, method: 'put', data })
export const deletePlantApi = (id) => request({ url: `/plants/delete/${id}`, method: 'delete' })

export const zoneListApi = () => request({ url: '/locations/zones/list', method: 'get' })
export const createZoneApi = (data) => request({ url: '/locations/zones/create', method: 'post', data })
export const updateZoneApi = (id, data) => request({ url: `/locations/zones/update/${id}`, method: 'put', data })
export const deleteZoneApi = (id) => request({ url: `/locations/zones/delete/${id}`, method: 'delete' })
export const zoneLocationListApi = (zoneId) => request({ url: `/locations/zones/${zoneId}/locations/list`, method: 'get' })
export const createZoneLocationApi = (zoneId, data) => request({ url: `/locations/zones/${zoneId}/locations/create`, method: 'post', data })
export const updateLocationApi = (id, data) => request({ url: `/locations/update/${id}`, method: 'put', data })
export const deleteLocationApi = (id) => request({ url: `/locations/delete/${id}`, method: 'delete' })
export const locationHierarchyApi = () => request({ url: '/locations/hierarchy', method: 'get' })

export const careMethodListApi = (params) => request({ url: '/care/methods/list', method: 'get', params })
export const createCareMethodApi = (data) => request({ url: '/care/methods/create', method: 'post', data })
export const updateCareMethodApi = (id, data) => request({ url: `/care/methods/update/${id}`, method: 'put', data })
export const deleteCareMethodApi = (id) => request({ url: `/care/methods/delete/${id}`, method: 'delete' })
export const reminderListApi = (params) => request({ url: '/care/reminders/list', method: 'get', params })
export const processReminderApi = (id, data) => request({ url: `/care/reminders/process/${id}`, method: 'post', data })

export const feedbackTypesApi = () => request({ url: '/feedbacks/types', method: 'get' })
export const submitFeedbackApi = (data) => request({ url: '/feedbacks/submit', method: 'post', data })
export const myFeedbackApi = (params) => request({ url: '/feedbacks/my', method: 'get', params })
export const feedbackListApi = (params) => request({ url: '/feedbacks/list', method: 'get', params })
export const auditFeedbackApi = (id, data) => request({ url: `/feedbacks/audit/${id}`, method: 'post', data })

export const userListApi = (params) => request({ url: '/users/list', method: 'get', params })
export const createUserApi = async (data) => request({ url: '/users/create', method: 'post', data: await encryptedUserPayload(data) })
export const updateUserApi = async (id, data) => request({ url: `/users/update/${id}`, method: 'put', data: await encryptedUserPayload(data) })

export const logListApi = (params) => request({ url: '/logs/list', method: 'get', params })

export const accessMatrixApi = () => request({ url: '/access/features/list', method: 'get' })
export const updateAccessApi = (data) => request({ url: '/access/features/update', method: 'put', data })
export const hashPasswordApi = async (data) => ({ data: { hashValue: hashPasswordText(data?.rawPassword || '') } })

