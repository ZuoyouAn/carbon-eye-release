import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { PLANETS, positionAt } from './planets'
import { surfaceTint } from './surface'
import { visibleLabels } from './labels'
export function createSolarScene(container, select) {
  const canvas = document.createElement('canvas'), context = canvas.getContext('webgl2', { antialias: true, alpha: false, powerPreference: 'low-power' })
  if (!context) throw new Error('此设备未启用 WebGL 2。仍可使用下方的行星按钮阅读图谱。')
  const renderer = new THREE.WebGLRenderer({ canvas, context, antialias: true }); renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5)); renderer.outputColorSpace = THREE.SRGBColorSpace; container.appendChild(canvas)
  const scene = new THREE.Scene(); scene.background = new THREE.Color('#edf1f6')
  const camera = new THREE.PerspectiveCamera(42, 1, .1, 240); camera.position.set(0, 43, 43)
  const controls = new OrbitControls(camera, canvas); controls.enableDamping = false; controls.minDistance = 6; controls.maxDistance = 200; controls.maxPolarAngle = Math.PI * .49; controls.enablePan = false
  scene.add(new THREE.AmbientLight('#ffffff', 2.4))
  const light = new THREE.PointLight('#fff2d2', 140, 100, 1); light.position.set(0, 2, 0); scene.add(light)
  const geometries = [], materials = [], objects = [], labels = [], orbitLines = []
  function mesh(geometry, material, parent = scene) { geometries.push(geometry); materials.push(material); const object = new THREE.Mesh(geometry, material); parent.add(object); return object }
  mesh(new THREE.SphereGeometry(1.65, 32, 24), new THREE.MeshBasicMaterial({ color: '#eab957' }))
  const halo = mesh(new THREE.RingGeometry(1.95, 2.06, 64), new THREE.MeshBasicMaterial({ color: '#e2bd72', side: THREE.DoubleSide, transparent: true, opacity: .6 })); halo.rotation.x = Math.PI / 2
  const sunLabel = document.createElement('span'); sunLabel.className = 'solar-label'; sunLabel.textContent = '太阳'; sunLabel.style.pointerEvents = 'none'; container.appendChild(sunLabel); labels.push({ id: 'sun', node: sunLabel, object: { position: new THREE.Vector3(0, 2, 0) } })
  PLANETS.forEach(planet => {
    const sphere = new THREE.SphereGeometry(planet.radius, 48, 32), positions = sphere.attributes.position, colors = [], base = new THREE.Color(planet.color), color = new THREE.Color()
    for (let i = 0; i < positions.count; i++) { const tint = surfaceTint(planet.id, positions.getX(i) / planet.radius, positions.getY(i) / planet.radius, positions.getZ(i) / planet.radius); color.copy(tint.color ? new THREE.Color(tint.color) : base).multiplyScalar(tint.shade); colors.push(color.r, color.g, color.b) }
    sphere.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
    const object = mesh(sphere, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .8 })); object.userData.id = planet.id; objects.push(object)
    if (planet.id === 'saturn') { const ring = mesh(new THREE.RingGeometry(1.14, 1.8, 64), new THREE.MeshStandardMaterial({ color: '#c1ae87', side: THREE.DoubleSide, transparent: true, opacity: .65 }), object); ring.rotation.x = Math.PI / 2.4; ring.userData.id = planet.id }
    const points = Array.from({ length: 129 }, (_, i) => new THREE.Vector3(Math.cos(i / 128 * Math.PI * 2) * planet.orbit, 0, Math.sin(i / 128 * Math.PI * 2) * planet.orbit))
    const geometry = new THREE.BufferGeometry().setFromPoints(points), material = new THREE.LineBasicMaterial({ color: '#bdc8d6', transparent: true, opacity: .65 }); geometries.push(geometry); materials.push(material)
    const line = new THREE.Line(geometry, material); scene.add(line); orbitLines.push(line)
    const label = document.createElement('span'); label.className = 'solar-label'; label.textContent = planet.name; label.style.pointerEvents = 'none'; container.appendChild(label); labels.push({ id: planet.id, node: label, object })
  })
  const selection = mesh(new THREE.RingGeometry(.91, 1, 64), new THREE.MeshBasicMaterial({ color: '#387dc4', side: THREE.DoubleSide, transparent: true, opacity: .7 })); selection.rotation.x = -Math.PI / 2
  let time = 0, showLabels = true, width = 1, height = 1, disposed = false, press = null, overview = true, followId = '', viewMode = 'perspective', selectedId = 'earth'
  const lastFollow = new THREE.Vector3()
  const raycaster = new THREE.Raycaster(), pointer = new THREE.Vector2(), projected = new THREE.Vector3()
  function render() {
    if (disposed) return
    objects.forEach((object, i) => { const p = positionAt(PLANETS[i], time); object.position.set(p.x, 0, p.z); object.rotation.y = time * .1 })
    const selected = objects.find(object => object.userData.id === selectedId), selectedPlanet = PLANETS.find(planet => planet.id === selectedId)
    if (selected && selectedPlanet) { selection.position.copy(selected.position); selection.position.y = .01; selection.scale.setScalar(Math.max(.55, selectedPlanet.radius * 1.5)) }
    if (followId) { const object = objects.find(item => item.userData.id === followId); if (object) { const delta = object.position.clone().sub(lastFollow); camera.position.add(delta); controls.target.copy(object.position); lastFollow.copy(object.position) } }
    renderer.render(scene, camera)
    const placements = labels.map(({ id, node, object }) => {
      projected.copy(object.position); projected.y += 1.25; projected.project(camera)
      return { id, x: (projected.x + 1) * width / 2, y: (-projected.y + 1) * height / 2, width: node.textContent.length * 14 + 14, height: 26, priority: id === selectedId ? 3 : id === 'sun' ? 2 : 0, visible: showLabels && projected.z >= -1 && projected.z <= 1 }
    })
    const visible = visibleLabels(placements, width, height)
    labels.forEach(({ id, node }, i) => { node.hidden = !visible.has(id); node.style.transform = `translate(${placements[i].x}px, ${placements[i].y}px) translate(-50%,-50%)` })
  }
  function resetOverview() { const distance = 43 * Math.max(1, 1.18 / (width / height)); controls.target.set(0, 0, 0); camera.position.set(0, distance * (viewMode === 'top' ? 1.42 : 1), viewMode === 'top' ? .01 : distance); controls.update() }
  function resize() { width = Math.max(1, container.clientWidth); height = Math.max(1, container.clientHeight); renderer.setSize(width, height); camera.aspect = width / height; camera.updateProjectionMatrix(); if (overview) resetOverview(); render() }
  const observer = new ResizeObserver(resize); observer.observe(container)
  controls.addEventListener('change', render)
  function pointerDown(event) { overview = false; press = { x: event.clientX, y: event.clientY } }
  function pointerUp(event) {
    if (!press || Math.hypot(event.clientX - press.x, event.clientY - press.y) > 5) { press = null; return }
    press = null; const rect = canvas.getBoundingClientRect(); pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1)
    raycaster.setFromCamera(pointer, camera); const hit = raycaster.intersectObjects(objects, true)[0]; if (hit?.object.userData.id) select(hit.object.userData.id)
  }
  canvas.addEventListener('pointerdown', pointerDown); canvas.addEventListener('pointerup', pointerUp); resize()
  return {
    canvas, render,
    selected(id) { if (PLANETS.some(planet => planet.id === id)) selectedId = id; render() },
    update(seconds) { time = seconds; render() },
    labels(visible) { showLabels = visible; render() },
    highlight(ids = []) { orbitLines.forEach((line, i) => { const active = ids.includes(PLANETS[i].id); line.material.color.set(active ? '#387dc4' : '#bdc8d6'); line.material.opacity = active ? 1 : .65 }); render() },
    orbits(visible) { orbitLines.forEach(line => { line.visible = Boolean(visible) }); render() },
    view(mode) { viewMode = mode === 'top' ? 'top' : 'perspective'; followId = ''; overview = true; resetOverview(); render() },
    follow(id) { followId = ''; const object = objects.find(item => item.userData.id === id); if (object) { overview = false; controls.target.copy(object.position); camera.position.copy(object.position).add(viewMode === 'top' ? new THREE.Vector3(0, 6, .01) : new THREE.Vector3(0, 3, 4)); lastFollow.copy(object.position); followId = id; controls.update() } render() },
    reset() { followId = ''; overview = true; resetOverview(); render() },
    focus(id) { followId = ''; const object = objects.find(item => item.userData.id === id); if (object) { overview = false; controls.target.copy(object.position); camera.position.copy(object.position).add(viewMode === 'top' ? new THREE.Vector3(0, 6, .01) : new THREE.Vector3(0, 3, 4)); controls.update(); render() } },
    dispose() { disposed = true; observer.disconnect(); controls.removeEventListener('change', render); controls.dispose(); canvas.removeEventListener('pointerdown', pointerDown); canvas.removeEventListener('pointerup', pointerUp); geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose()); labels.forEach(({ node }) => node.remove()); renderer.dispose(); renderer.forceContextLoss(); canvas.remove() },
  }
}
