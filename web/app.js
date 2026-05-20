(function () {
  const inputList = document.getElementById("inputList");
  const inputRules = document.getElementById("inputRules");
  const outputPython = document.getElementById("outputPython");
  const btnGenerate = document.getElementById("btnGenerate");
  const btnCopy = document.getElementById("btnCopy");
  const message = document.getElementById("message");

  function setMessage(text, type = "ok") {
    message.textContent = text;
    message.className = type;
  }

  function toNumber(value) {
    return Number(String(value).replace(",", "."));
  }

  function parseLayer(text) {
    const match = text.match(/\bLayer\s*[:=]\s*"?([^"\r\n]+)"?/i);
    if (!match) throw new Error('Layer não encontrado. Use: Layer: "ALVENARIA"');
    return match[1].trim();
  }

  function parsePoints(text) {
    const points = [];

    const patterns = [
      /at\s+point\s*\(\s*([-+]?\d+(?:[.,]\d+)?)\s*,\s*([-+]?\d+(?:[.,]\d+)?)\s*,\s*([-+]?\d+(?:[.,]\d+)?)\s*\)/gi,
      /(?:at\s+point\s+)?X\s*=\s*([-+]?\d+(?:[.,]\d+)?)\s+Y\s*=\s*([-+]?\d+(?:[.,]\d+)?)\s+Z\s*=\s*([-+]?\d+(?:[.,]\d+)?)/gi
    ];

    for (const pattern of patterns) {
      let match;
      while ((match = pattern.exec(text)) !== null) {
        points.push({
          x: toNumber(match[1]),
          y: toNumber(match[2]),
          z: toNumber(match[3])
        });
      }
    }

    if (points.length < 3) {
      throw new Error("Pontos insuficientes. São necessários pelo menos 3 pontos X/Y/Z.");
    }

    return points;
  }

  function ensureClosedPolygon(points) {
    const first = points[0];
    const last = points[points.length - 1];

    if (first.x !== last.x || first.y !== last.y || first.z !== last.z) {
      return [...points, { ...first }];
    }

    return points;
  }

  function parseRules(text) {
    const match = text.match(/^([^\s]+)\s+z\s*=\s*([-+]?\d+(?:[.,]\d+)?)\s+extrude\s*=\s*([-+]?\d+(?:[.,]\d+)?)\s+cor\s+rgb\s+(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})$/im);

    if (!match) {
      throw new Error("Regra inválida. Use: ALVENARIA z=0 extrude=3 cor rgb 120,120,120");
    }

    const rgb = [Number(match[4]), Number(match[5]), Number(match[6])];

    if (rgb.some((v) => v < 0 || v > 255)) {
      throw new Error("RGB deve estar entre 0 e 255.");
    }

    return {
      layer: match[1].trim(),
      base_z: toNumber(match[2]),
      extrude: toNumber(match[3]),
      rgb
    };
  }

  function buildEspp(listText, rulesText) {
    const layer = parseLayer(listText);
    const points = ensureClosedPolygon(parsePoints(listText));
    const rule = parseRules(rulesText);

    if (layer.toUpperCase() !== rule.layer.toUpperCase()) {
      throw new Error(`A regra é para "${rule.layer}", mas o LIST está na layer "${layer}".`);
    }

    return {
      protocol: "ESPP",
      version: "MVP_FENIX_V02",
      objects: [
        {
          type: "POLYLINE",
          name: `${layer}_001`,
          layer,
          points,
          base_z: rule.base_z,
          extrude: rule.extrude,
          color: rule.rgb
        }
      ]
    };
  }

  function generateBlenderPython(espp) {
    const obj = espp.objects[0];
    const verts = obj.points.slice(0, -1)
      .map((p) => `(${p.x}, ${p.y}, ${obj.base_z})`)
      .join(",\n    ");

    const face = obj.points.slice(0, -1).map((_, i) => i).join(", ");
    const rgb = obj.color.map((v) => v / 255);

    return `import bpy

# TEMPO ENGINE / ESPP — MVP FÊNIX V02

mesh = bpy.data.meshes.new("${obj.name}_mesh")
obj = bpy.data.objects.new("${obj.name}", mesh)
bpy.context.collection.objects.link(obj)

verts = [
    ${verts}
]

faces = [(${face})]

mesh.from_pydata(verts, [], faces)
mesh.update()

solidify = obj.modifiers.new(name="Solidify", type="SOLIDIFY")
solidify.thickness = ${obj.extrude}

mat = bpy.data.materials.new(name="${obj.layer}_mat")
mat.diffuse_color = (${rgb[0]}, ${rgb[1]}, ${rgb[2]}, 1.0)
obj.data.materials.append(mat)

print("Tempo Engine: geometria criada com sucesso.")
`;
  }

  btnGenerate.addEventListener("click", function () {
    try {
      const espp = buildEspp(inputList.value, inputRules.value);
      outputPython.value = generateBlenderPython(espp);
      setMessage("Python Blender gerado com sucesso.", "ok");
    } catch (error) {
      outputPython.value = "";
      setMessage(error.message, "error");
    }
  });

  btnCopy.addEventListener("click", async function () {
    if (!outputPython.value.trim()) {
      setMessage("Nada para copiar.", "error");
      return;
    }

    await navigator.clipboard.writeText(outputPython.value);
    setMessage("Python copiado.", "ok");
  });
})();
