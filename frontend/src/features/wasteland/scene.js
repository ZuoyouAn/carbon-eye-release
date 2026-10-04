import * as THREE from 'three'
import { WORLD } from './expedition'
import { expeditionObjective } from './navigation'

// All scenery is original procedural geometry; no downloaded models or textures.
export function createWastelandScene(container, state) {
  const canvas = document.createElement('canvas')
  const context = canvas.getContext('webgl2', { antialias: true, alpha: false, powerPreference: 'low-power' })
  if (!context) throw new Error('此设备未启用 WebGL 2，可切换到「三十天剧情」继续游玩。')
  const renderer = new THREE.WebGLRenderer({ canvas, context, antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.outputColorSpace = THREE.SRGBColorSpace
  container.appendChild(canvas)
  const scene = new THREE.Scene()
  scene.background = new THREE.Color('#e5eceb')
  scene.fog = new THREE.Fog('#e5eceb', 42, 85)
  const camera = new THREE.OrthographicCamera(-18, 18, 18, -18, .1, 100)
  const geometries = new Set(), materials = new Map()
  const material = color => {
    if (!materials.has(color)) materials.set(color, new THREE.MeshStandardMaterial({ color, roughness: .9 }))
    return materials.get(color)
  }
  function mesh(geometry, color, x, y, z, parent = scene) {
    geometries.add(geometry)
    const object = new THREE.Mesh(geometry, material(color))
    object.position.set(x, y, z); object.castShadow = true; object.receiveShadow = true; parent.add(object)
    return object
  }
  const box = (w, h, d, color, x, y, z, parent) => mesh(new THREE.BoxGeometry(w, h, d), color, x, y, z, parent)
  const cylinder = (r, h, color, x, y, z, parent) => mesh(new THREE.CylinderGeometry(r, r, h, 8), color, x, y, z, parent)
  const ring = (r, color, x, z) => {
    const object = mesh(new THREE.RingGeometry(r - .08, r, 48), color, x, .025, z)
    object.rotation.x = -Math.PI / 2; return object
  }
  scene.add(new THREE.HemisphereLight('#ffffff', '#9caea0', 2.6))
  const sun = new THREE.DirectionalLight('#fff5df', 3)
  sun.position.set(-12, 22, 14); sun.castShadow = true
  sun.shadow.mapSize.set(1024, 1024)
  Object.assign(sun.shadow.camera, { left: -24, right: 24, top: 24, bottom: -24, far: 70 })
  sun.shadow.normalBias = .04; scene.add(sun)
  box(36, .2, 36, '#cbd5bc', 0, -.12, 0)
  box(4, .03, 35, '#e9e8df', 0, .005, 0); box(35, .03, 4, '#e9e8df', 0, .005, 0)
  box(35, .025, 2, '#dde0cf', 0, .005, 12); box(2, .025, 35, '#dde0cf', -12, .005, 0)
  for (const b of WORLD.buildings) {
    box(b.w, b.h, b.d, '#c2bbaa', b.x, b.h / 2, b.z)
    box(b.w + .3, .25, b.d + .3, '#f4eee2', b.x, b.h, b.z)
    box(b.w * .55, .8, b.d * .4, '#d3ccbb', b.x, b.h + .4, b.z)
    for (let i = -1; i <= 1; i++) box(.55, .8, .06, '#8ba1a2', b.x + i * b.w / 3, b.h * .62, b.z + b.d / 2 + .04)
    box(.8, 1.5, .06, '#7e908b', b.x, .75, b.z + b.d / 2 + .05)
  }
  for (const [x, z] of [[-16, -15], [-16, 0], [-16, 8], [-5, 6], [-4, -14], [5, 15], [15, 14], [15, 6], [16, -5], [5, -16], [-12, 15]]) {
    cylinder(.15, 1.6, '#8d8570', x, .8, z)
    mesh(new THREE.IcosahedronGeometry(1.15, 0), '#91a58c', x, 2.1, z)
  }
  const tent = mesh(new THREE.ConeGeometry(1.5, 1.7, 4), '#e5b47a', -14, .85, 12); tent.rotation.y = Math.PI / 4
  ring(1.4, '#6a9988', WORLD.spawn.x, WORLD.spawn.z)
  const exit = cylinder(1.6, .06, '#9dbaa4', WORLD.exit.x, .03, WORLD.exit.z)
  for (const dx of [-1.8, 1.8]) {
    cylinder(.07, 3, '#798f8e', WORLD.exit.x + dx, 1.5, WORLD.exit.z)
    box(.6, .5, .04, '#458a71', WORLD.exit.x + dx + .25, 2.7, WORLD.exit.z)
  }
  cylinder(.18, 4.2, '#829397', WORLD.beacon.x, 2.1, WORLD.beacon.z)
  box(2.3, .2, .2, '#a9bcc0', WORLD.beacon.x, 3.7, WORLD.beacon.z)
  const beam = cylinder(.3, 6, '#87cbf5', WORLD.beacon.x, 6.8, WORLD.beacon.z)
  ring(1.4, '#6a9eb8', WORLD.beacon.x, WORLD.beacon.z)
  const objectiveRing = ring(1.1, '#c49b42', 0, 0)
  for (const [x, z] of [[-3, 12], [3, 0], [-12, 2], [3, -10]]) {
    cylinder(.07, 2.8, '#657d80', x, 1.4, z)
    box(.6, .1, .4, '#f5ecd2', x + .2, 2.8, z)
  }
  const pickups = state.loot.map(item => {
    const group = new THREE.Group(); group.position.set(item.x, .5, item.z); scene.add(group)
    if (item.kind === 'cell') { cylinder(.28, .7, '#5bafe0', 0, 0, 0, group); cylinder(.18, .1, '#e2f5ff', 0, .4, 0, group) }
    else {
      box(.8, .7, .7, item.kind === 'med' ? '#fcfcf5' : '#b59261', 0, 0, 0, group)
      box(.15, .72, .72, item.kind === 'med' ? '#c67265' : '#e5ce9d', 0, 0, 0, group)
      if (item.kind === 'med') box(.5, .15, .72, '#c67265', 0, 0, 0, group)
    }
    ring(.65, item.kind === 'cell' ? '#6dafe0' : '#bca578', item.x, item.z)
    return group
  })
  const player = new THREE.Group(); scene.add(player)
  box(.55, .7, .35, '#5084ba', 0, .9, 0, player)
  box(.44, .5, .18, '#d9b188', 0, .92, -.24, player)
  mesh(new THREE.SphereGeometry(.22, 10, 8), '#edc9a2', 0, 1.5, 0, player)
  cylinder(.27, .12, '#e9e3d5', 0, 1.69, 0, player)
  const legs = [-1, 1].map(side => box(.19, .5, .22, '#637b88', side * .16, .3, 0, player))
  for (const side of [-1, 1]) box(.15, .5, .18, '#5084ba', side * .36, .91, 0, player)
  const drones = state.enemies.map(() => {
    const group = new THREE.Group(); scene.add(group)
    box(.85, .38, .55, '#859797', 0, 0, 0, group)
    box(.3, .1, .06, '#ca7365', 0, 0, .3, group)
    for (const dx of [-.65, .65]) cylinder(.35, .06, '#677d80', dx, .15, 0, group)
    return group
  })
  let width = 1, height = 1, disposed = false, onResize = () => {}
  function resize() {
    width = Math.max(1, container.clientWidth); height = Math.max(1, container.clientHeight)
    renderer.setSize(width, height); onResize()
  }
  const observer = new ResizeObserver(resize); observer.observe(container); resize()
  return {
    set onResize(callback) { onResize = callback },
    render(current, yaw = Math.PI / 4, zoom = 18, reducedMotion = false, moving = false) {
      if (disposed) return
      const p = current.player, aspect = width / height
      const objective = expeditionObjective(current)
      objectiveRing.visible = Boolean(objective) && current.status === 'playing'
      if (objective) objectiveRing.position.set(objective.x, .04, objective.z)
      camera.left = -zoom * aspect; camera.right = zoom * aspect; camera.top = zoom; camera.bottom = -zoom; camera.updateProjectionMatrix()
      const cx = Math.max(-7, Math.min(7, p.x * .5)), cz = Math.max(-7, Math.min(7, p.z * .5))
      camera.position.set(cx + Math.sin(yaw) * 27, 24, cz + Math.cos(yaw) * 27); camera.lookAt(cx, 0, cz)
      player.position.set(p.x, 0, p.z); player.rotation.y = p.facing
      legs.forEach((leg, i) => { leg.rotation.x = moving && !reducedMotion ? Math.sin(current.elapsed * 15 + i * Math.PI) * .4 : 0 })
      pickups.forEach((group, i) => { group.visible = !current.loot[i].taken; group.rotation.y = reducedMotion ? 0 : current.elapsed * .3 })
      drones.forEach((group, i) => { group.position.set(current.enemies[i].x, 1.1 + (reducedMotion ? 0 : Math.sin(current.elapsed * 3 + i) * .12), current.enemies[i].z) })
      beam.visible = current.repaired; exit.material = material(current.repaired ? '#4d9e83' : '#9dbaa4')
      renderer.render(scene, camera)
    },
    dispose() {
      disposed = true; observer.disconnect()
      for (const geometry of geometries) geometry.dispose()
      for (const m of materials.values()) m.dispose()
      renderer.dispose(); renderer.forceContextLoss(); canvas.remove()
    },
    canvas,
    get modelCount() { return renderer.info.render.triangles },
  }
}
