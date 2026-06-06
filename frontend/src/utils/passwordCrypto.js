const PASSWORD_RSA_PUBLIC_KEY_BASE64 = String(__PASSWORD_RSA_PUBLIC_KEY_BASE64_FROM_SOURCE__ || '')
const SHA256_BLOCK_SIZE = 64
const SHA256_OUTPUT_SIZE = 32

function base64ToBytes(base64Text) {
  const cleanText = String(base64Text || '').trim()
  if (!/^[A-Za-z0-9+/=]+$/.test(cleanText)) {
    throw new Error('The password transport public key must be a continuous Base64 key body.')
  }
  const binaryText = atob(cleanText)
  const bytes = new Uint8Array(binaryText.length)
  for (let index = 0; index < binaryText.length; index += 1) bytes[index] = binaryText.charCodeAt(index)
  return bytes
}

function bytesToBase64(bytes) {
  let binaryText = ''
  for (let index = 0; index < bytes.length; index += 1) binaryText += String.fromCharCode(bytes[index])
  return btoa(binaryText)
}

function textToBytes(text) {
  return new TextEncoder().encode(String(text ?? ''))
}

function concatBytes(...items) {
  let length = 0
  for (const item of items) length += item.length
  const out = new Uint8Array(length)
  let offset = 0
  for (const item of items) {
    out.set(item, offset)
    offset += item.length
  }
  return out
}

function rightRotate(value, bits) {
  return (value >>> bits) | (value << (32 - bits))
}

function sha256(data) {
  const k = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
  ]
  const h = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
  const bitLength = data.length * 8
  const paddedLength = Math.ceil((data.length + 9) / SHA256_BLOCK_SIZE) * SHA256_BLOCK_SIZE
  const padded = new Uint8Array(paddedLength)
  padded.set(data)
  padded[data.length] = 0x80
  const view = new DataView(padded.buffer)
  view.setUint32(paddedLength - 8, Math.floor(bitLength / 0x100000000), false)
  view.setUint32(paddedLength - 4, bitLength >>> 0, false)
  const w = new Uint32Array(64)
  for (let offset = 0; offset < paddedLength; offset += SHA256_BLOCK_SIZE) {
    for (let index = 0; index < 16; index += 1) w[index] = view.getUint32(offset + index * 4, false)
    for (let index = 16; index < 64; index += 1) {
      const s0 = rightRotate(w[index - 15], 7) ^ rightRotate(w[index - 15], 18) ^ (w[index - 15] >>> 3)
      const s1 = rightRotate(w[index - 2], 17) ^ rightRotate(w[index - 2], 19) ^ (w[index - 2] >>> 10)
      w[index] = (w[index - 16] + s0 + w[index - 7] + s1) >>> 0
    }
    let a = h[0]
    let b = h[1]
    let c = h[2]
    let d = h[3]
    let e = h[4]
    let f = h[5]
    let g = h[6]
    let hh = h[7]
    for (let index = 0; index < 64; index += 1) {
      const s1 = rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25)
      const ch = (e & f) ^ (~e & g)
      const temp1 = (hh + s1 + ch + k[index] + w[index]) >>> 0
      const s0 = rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22)
      const maj = (a & b) ^ (a & c) ^ (b & c)
      const temp2 = (s0 + maj) >>> 0
      hh = g
      g = f
      f = e
      e = (d + temp1) >>> 0
      d = c
      c = b
      b = a
      a = (temp1 + temp2) >>> 0
    }
    h[0] = (h[0] + a) >>> 0
    h[1] = (h[1] + b) >>> 0
    h[2] = (h[2] + c) >>> 0
    h[3] = (h[3] + d) >>> 0
    h[4] = (h[4] + e) >>> 0
    h[5] = (h[5] + f) >>> 0
    h[6] = (h[6] + g) >>> 0
    h[7] = (h[7] + hh) >>> 0
  }
  const out = new Uint8Array(SHA256_OUTPUT_SIZE)
  const outView = new DataView(out.buffer)
  for (let index = 0; index < 8; index += 1) outView.setUint32(index * 4, h[index], false)
  return out
}

function mgf1(seed, length) {
  const out = new Uint8Array(length)
  let offset = 0
  let counter = 0
  while (offset < length) {
    const counterBytes = new Uint8Array(4)
    new DataView(counterBytes.buffer).setUint32(0, counter, false)
    const digest = sha256(concatBytes(seed, counterBytes))
    out.set(digest.slice(0, Math.min(digest.length, length - offset)), offset)
    offset += digest.length
    counter += 1
  }
  return out
}

function xorBytes(left, right) {
  const out = new Uint8Array(left.length)
  for (let index = 0; index < left.length; index += 1) out[index] = left[index] ^ right[index]
  return out
}

function randomBytes(length) {
  if (!globalThis.crypto || typeof globalThis.crypto.getRandomValues !== 'function') {
    throw new Error('This browser cannot finish password protection for this submission.')
  }
  const out = new Uint8Array(length)
  globalThis.crypto.getRandomValues(out)
  return out
}

function readDerLength(bytes, offset) {
  let length = bytes[offset]
  offset += 1
  if ((length & 0x80) === 0) return { length, offset }
  const size = length & 0x7f
  length = 0
  for (let index = 0; index < size; index += 1) {
    length = length * 256 + bytes[offset]
    offset += 1
  }
  return { length, offset }
}

function readDer(bytes, offset) {
  const tag = bytes[offset]
  const lengthInfo = readDerLength(bytes, offset + 1)
  const start = lengthInfo.offset
  const end = start + lengthInfo.length
  return { tag, start, end, next: end }
}

function trimIntegerBytes(bytes) {
  let offset = 0
  while (offset < bytes.length - 1 && bytes[offset] === 0) offset += 1
  return bytes.slice(offset)
}

function parsePublicKey(base64Text) {
  const spki = base64ToBytes(base64Text)
  const top = readDer(spki, 0)
  const algorithm = readDer(spki, top.start)
  const bitString = readDer(spki, algorithm.next)
  if (top.tag !== 0x30 || bitString.tag !== 0x03 || spki[bitString.start] !== 0) throw new Error('The password transport public key is not valid.')
  const rsaBytes = spki.slice(bitString.start + 1, bitString.end)
  const rsa = readDer(rsaBytes, 0)
  const modulusItem = readDer(rsaBytes, rsa.start)
  const exponentItem = readDer(rsaBytes, modulusItem.next)
  if (rsa.tag !== 0x30 || modulusItem.tag !== 0x02 || exponentItem.tag !== 0x02) throw new Error('The password transport public key is not valid.')
  const modulusBytes = trimIntegerBytes(rsaBytes.slice(modulusItem.start, modulusItem.end))
  const exponentBytes = trimIntegerBytes(rsaBytes.slice(exponentItem.start, exponentItem.end))
  return { modulus: bytesToBigInt(modulusBytes), exponent: bytesToBigInt(exponentBytes), size: modulusBytes.length }
}

function bytesToBigInt(bytes) {
  let value = 0n
  for (const item of bytes) value = (value << 8n) + BigInt(item)
  return value
}

function bigIntToBytes(value, size) {
  const out = new Uint8Array(size)
  let current = value
  for (let index = size - 1; index >= 0; index -= 1) {
    out[index] = Number(current & 0xffn)
    current >>= 8n
  }
  return out
}

function modPow(base, exponent, modulus) {
  let result = 1n
  let currentBase = base % modulus
  let currentExponent = exponent
  while (currentExponent > 0n) {
    if ((currentExponent & 1n) === 1n) result = (result * currentBase) % modulus
    currentBase = (currentBase * currentBase) % modulus
    currentExponent >>= 1n
  }
  return result
}

let cachedKey = null

function encryptWithRsaOaepSha256(text) {
  if (!cachedKey) cachedKey = parsePublicKey(PASSWORD_RSA_PUBLIC_KEY_BASE64)
  const message = textToBytes(text)
  const k = cachedKey.size
  const hLen = SHA256_OUTPUT_SIZE
  if (message.length > k - 2 * hLen - 2) throw new Error('The password content is too long.')
  const lHash = sha256(new Uint8Array(0))
  const ps = new Uint8Array(k - message.length - 2 * hLen - 2)
  const db = concatBytes(lHash, ps, new Uint8Array([1]), message)
  const seed = randomBytes(hLen)
  const maskedDB = xorBytes(db, mgf1(seed, k - hLen - 1))
  const maskedSeed = xorBytes(seed, mgf1(maskedDB, hLen))
  const encoded = concatBytes(new Uint8Array([0]), maskedSeed, maskedDB)
  const encryptedNumber = modPow(bytesToBigInt(encoded), cachedKey.exponent, cachedKey.modulus)
  return bytesToBase64(bigIntToBytes(encryptedNumber, k))
}

function bytesToHex(bytes) {
  return Array.from(bytes, item => item.toString(16).padStart(2, '0')).join('')
}

export function hashPasswordText(value) {
  return bytesToHex(sha256(textToBytes(String(value ?? ''))))
}

export async function encryptPasswordText(value) {
  const text = String(value ?? '')
  if (!text) return ''
  return encryptWithRsaOaepSha256(text)
}

async function buildEncryptedPasswordField(encryptedFieldName, value) {
  const text = String(value ?? '')
  if (!text) return {}
  return { [encryptedFieldName]: await encryptPasswordText(text) }
}

export async function encryptedLoginPayload(form) {
  return { username: String(form?.username || '').trim(), ...(await buildEncryptedPasswordField('encryptedPassword', form?.password || '')) }
}

export async function encryptedRegisterPayload(form) {
  return {
    username: String(form?.username || '').trim(),
    realName: String(form?.realName || '').trim(),
    phone: form?.phone || '',
    email: String(form?.email || '').trim(),
    ...(await buildEncryptedPasswordField('encryptedPassword', form?.password || '')),
    ...(await buildEncryptedPasswordField('encryptedConfirmPassword', form?.confirmPassword || ''))
  }
}

export async function encryptedProfilePasswordPayload(form) {
  return {
    ...(await buildEncryptedPasswordField('encryptedOldPassword', form?.oldPassword || '')),
    ...(await buildEncryptedPasswordField('encryptedNewPassword', form?.newPassword || '')),
    ...(await buildEncryptedPasswordField('encryptedConfirmPassword', form?.confirmPassword || ''))
  }
}

export async function encryptedUserPayload(form) {
  const payload = { ...form }
  delete payload.password
  delete payload.confirmPassword
  delete payload.oldPassword
  delete payload.newPassword
  delete payload.rawPassword
  delete payload.hashValue
  if (form?.password) Object.assign(payload, await buildEncryptedPasswordField('encryptedPassword', form.password))
  return payload
}

