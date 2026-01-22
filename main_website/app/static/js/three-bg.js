// IntelliPrep - Three.js Animated Background
// Creates smooth, beautiful 3D animations

const ColorPalettes = {
  palette1: {
    // Purple to Pink
    colors: [0x667eea, 0x764ba2, 0xf093fb, 0xf5576c],
    name: 'Purple Pink'
  },
  palette2: {
    // Cyan to Purple
    colors: [0x00d2fc, 0x3a47d5, 0x00d2fc, 0x928dab],
    name: 'Cyan Purple'
  },
  palette3: {
    // Ocean
    colors: [0x0077be, 0x00a8e8, 0x00c9ff, 0x92e1ff],
    name: 'Ocean'
  },
  palette4: {
    // Sunset
    colors: [0xff6b6b, 0xffa94d, 0xffd93d, 0xff8c42],
    name: 'Sunset'
  },
  palette5: {
    // Forest
    colors: [0x11998e, 0x38ef7d, 0x0d7377, 0x14cc80],
    name: 'Forest'
  }
};

class IntelliPrepBackground {
  constructor() {
    this.container = document.body;
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.particles = null;
    this.geometries = [];
    this.currentPalette = ColorPalettes.palette1;
    this.time = 0;
    this.rotationSpeed = 0.0005;
    
    this.init();
    this.animate();
    this.setupResizeListener();
  }

  init() {
    // Scene setup
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0f0f23);
    this.scene.fog = new THREE.Fog(0x0f0f23, 100, 1000);

    // Camera setup
    this.camera = new THREE.PerspectiveCamera(
      75,
      window.innerWidth / window.innerHeight,
      0.1,
      1000
    );
    this.camera.position.z = 30;

    // Renderer setup
    this.renderer = new THREE.WebGLRenderer({ 
      antialias: true, 
      alpha: true,
      precision: 'highp'
    });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowShadowMap;
    
    const canvas = this.renderer.domElement;
    canvas.id = 'canvas-bg';
    document.body.appendChild(canvas);

    // Lighting
    this.setupLighting();

    // Create geometries
    this.createParticles();
    this.createFloatingObjects();
    this.createWaveEffect();
  }

  setupLighting() {
    // Ambient light
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    this.scene.add(ambientLight);

    // Point lights
    const pointLight1 = new THREE.PointLight(this.currentPalette.colors[0], 1, 100);
    pointLight1.position.set(20, 30, 20);
    this.scene.add(pointLight1);

    const pointLight2 = new THREE.PointLight(this.currentPalette.colors[2], 1, 100);
    pointLight2.position.set(-20, -30, 10);
    this.scene.add(pointLight2);

    // Directional light for atmosphere
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.3);
    directionalLight.position.set(10, 20, 10);
    this.scene.add(directionalLight);
  }

  createParticles() {
    const particleCount = 200;
    const geometry = new THREE.BufferGeometry();

    const positionArray = new Float32Array(particleCount * 3);
    const colorArray = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      positionArray[i * 3] = (Math.random() - 0.5) * 100;
      positionArray[i * 3 + 1] = (Math.random() - 0.5) * 100;
      positionArray[i * 3 + 2] = (Math.random() - 0.5) * 100;

      const color = new THREE.Color(
        this.currentPalette.colors[Math.floor(Math.random() * this.currentPalette.colors.length)]
      );
      colorArray[i * 3] = color.r;
      colorArray[i * 3 + 1] = color.g;
      colorArray[i * 3 + 2] = color.b;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positionArray, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colorArray, 3));

    const material = new THREE.PointsMaterial({
      size: 0.3,
      vertexColors: true,
      transparent: true,
      opacity: 0.6,
      sizeAttenuation: true
    });

    this.particles = new THREE.Points(geometry, material);
    this.scene.add(this.particles);
  }

  createFloatingObjects() {
    const geometries = [
      new THREE.IcosahedronGeometry(2, 4),
      new THREE.TetrahedronGeometry(2),
      new THREE.OctahedronGeometry(2),
      new THREE.DodecahedronGeometry(1.5, 0)
    ];

    for (let i = 0; i < 4; i++) {
      const geometry = geometries[i];
      const color = this.currentPalette.colors[i % this.currentPalette.colors.length];

      const material = new THREE.MeshPhongMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 0.3,
        wireframe: false,
        shininess: 100,
        transparent: true,
        opacity: 0.7
      });

      const mesh = new THREE.Mesh(geometry, material);
      
      mesh.position.x = (Math.random() - 0.5) * 60;
      mesh.position.y = (Math.random() - 0.5) * 60;
      mesh.position.z = (Math.random() - 0.5) * 60;

      mesh.userData.rotationSpeed = {
        x: Math.random() * 0.002,
        y: Math.random() * 0.003,
        z: Math.random() * 0.002
      };

      mesh.userData.originalPosition = {
        x: mesh.position.x,
        y: mesh.position.y,
        z: mesh.position.z
      };

      this.geometries.push(mesh);
      this.scene.add(mesh);
    }
  }

  createWaveEffect() {
    const waveGeometry = new THREE.PlaneGeometry(100, 100, 50, 50);
    const waveMaterial = new THREE.MeshPhongMaterial({
      color: 0x667eea,
      emissive: 0x667eea,
      emissiveIntensity: 0.2,
      wireframe: true,
      transparent: true,
      opacity: 0.1
    });

    const waveMesh = new THREE.Mesh(waveGeometry, waveMaterial);
    waveMesh.rotation.x = -Math.PI / 3;
    waveMesh.position.z = -30;
    waveMesh.userData.isWave = true;

    this.geometries.push(waveMesh);
    this.scene.add(waveMesh);
  }

  animate() {
    requestAnimationFrame(() => this.animate());

    this.time += 0.001;

    // Rotate particles
    if (this.particles) {
      this.particles.rotation.x += this.rotationSpeed * 0.5;
      this.particles.rotation.y += this.rotationSpeed;

      // Wave particles up and down
      const positions = this.particles.geometry.attributes.position.array;
      for (let i = 0; i < positions.length; i += 3) {
        positions[i + 1] += Math.sin(this.time * 2 + i) * 0.01;
      }
      this.particles.geometry.attributes.position.needsUpdate = true;
    }

    // Rotate and animate geometries
    this.geometries.forEach((mesh, index) => {
      if (mesh.userData.isWave) {
        // Wave animation
        const positions = mesh.geometry.attributes.position.array;
        const originalPositions = mesh.geometry.userData.originalPositions || positions.slice();
        
        if (!mesh.geometry.userData.originalPositions) {
          mesh.geometry.userData.originalPositions = originalPositions;
        }

        for (let i = 0; i < positions.length; i += 3) {
          positions[i + 2] = originalPositions[i + 2] + 
            Math.sin((originalPositions[i] + this.time * 5) * 0.05) * 
            Math.cos((originalPositions[i + 1] + this.time * 3) * 0.05) * 2;
        }
        mesh.geometry.attributes.position.needsUpdate = true;
      } else {
        // Rotate geometries
        mesh.rotation.x += mesh.userData.rotationSpeed.x;
        mesh.rotation.y += mesh.userData.rotationSpeed.y;
        mesh.rotation.z += mesh.userData.rotationSpeed.z;

        // Bob up and down
        mesh.position.y = mesh.userData.originalPosition.y + Math.sin(this.time * 1.5 + index) * 3;
        mesh.position.x = mesh.userData.originalPosition.x + Math.cos(this.time * 1 + index * 0.5) * 2;
      }
    });

    this.renderer.render(this.scene, this.camera);
  }

  setupResizeListener() {
    window.addEventListener('resize', () => {
      this.camera.aspect = window.innerWidth / window.innerHeight;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(window.innerWidth, window.innerHeight);
    });
  }

  changePalette(paletteKey) {
    this.currentPalette = ColorPalettes[paletteKey];
    
    // Update particle colors
    if (this.particles) {
      const colorArray = this.particles.geometry.attributes.color.array;
      const particleCount = colorArray.length / 3;

      for (let i = 0; i < particleCount; i++) {
        const color = new THREE.Color(
          this.currentPalette.colors[Math.floor(Math.random() * this.currentPalette.colors.length)]
        );
        colorArray[i * 3] = color.r;
        colorArray[i * 3 + 1] = color.g;
        colorArray[i * 3 + 2] = color.b;
      }
      this.particles.geometry.attributes.color.needsUpdate = true;
    }

    // Update geometry colors
    this.geometries.forEach((mesh, index) => {
      if (mesh.material && !mesh.userData.isWave) {
        const newColor = this.currentPalette.colors[index % this.currentPalette.colors.length];
        mesh.material.color.setHex(newColor);
        mesh.material.emissive.setHex(newColor);
      }
    });
  }
}

// Initialize when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.intelliprepBg = new IntelliPrepBackground();
  });
} else {
  window.intelliprepBg = new IntelliPrepBackground();
}

// Pause animation when tab is not visible
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    if (window.intelliprepBg) {
      window.intelliprepBg.renderer.setAnimationLoop(null);
    }
  } else {
    if (window.intelliprepBg) {
      window.intelliprepBg.animate();
    }
  }
});