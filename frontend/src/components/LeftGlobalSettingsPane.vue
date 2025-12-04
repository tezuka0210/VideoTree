<template>
  <section class="w-full h-full bg-white rounded-lg shadow-inner flex flex-col">
    <header class="px-2.5 py-2 border-b border-gray-100">
      <h2 class="text-xs font-semibold text-gray-700 tracking-wide">Global Model Settings</h2>
    </header>

    <div class="flex-1 min-h-0 overflow-y-auto px-2.5 py-2 space-y-3 text-xs">
      
      <div class="space-y-1">
        <label class="block text-[10px] uppercase font-bold text-gray-400">Model</label>
        <select class="w-full border border-gray-200 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white">
          <option>video-llm-1</option>
          <option>image-llm-1</option>
          <option>custom-v2</option>
        </select>
      </div>

      <div class="space-y-1">
        <label class="block text-[10px] uppercase font-bold text-gray-400">Temperature</label>
        <div class="flex items-center gap-2">
           <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            class="flex-1 h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <input
            type="number"
            min="0"
            max="1"
            step="0.1"
            class="w-10 border border-gray-200 rounded px-1 py-0.5 text-center focus:outline-none"
            placeholder="0.7"
          />
        </div>
      </div>

      <div class="space-y-1">
        <label class="block text-[10px] uppercase font-bold text-gray-400">Style</label>
        <select class="w-full border border-gray-200 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white">
          <option>Realistic & Photography</option>
          <option>Cyber & Sci-Fi</option>
          <option>Anime & Cel-Shaded</option>
          <option>Pixar & 3D Cartoon</option>
          <option>Art History & Painterly</option>
          <option>Dark & Horror</option>
          <option>GuFeng Classic</option>
        </select>
      </div>

      <div class="space-y-1">
        <label class="block text-[10px] uppercase font-bold text-gray-400">Mood</label>
        <select class="w-full border border-gray-200 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white">
          <option value="joyful">Joyful</option>
          <option value="melancholic">Melancholic</option>
          <option value="epic">Epic</option>
          <option value="eerie">Eerie</option>
          <option value="serene">Serene</option>
        </select>
      </div>

      <div class="space-y-1">
        <label class="block text-[10px] uppercase font-bold text-gray-400">Palette</label>
        <select class="w-full border border-gray-200 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white">
          <option value="warm">Warm</option>
          <option value="cool">Cool</option>
          <option value="monochrome">Monochrome</option>
          <option value="pastel">Pastel</option>
        </select>
      </div>

      <div class="space-y-1 pt-1">
        <label class="block text-[10px] uppercase font-bold text-gray-400">Reference Materials</label>
        <textarea
          rows="5"
          class="w-full border border-gray-200 rounded px-2 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-gray-50 leading-relaxed"
          placeholder="Paste your reference text, cultural context, or historical background here..."
        ></textarea>
      </div>

    </div>
    
    <div class="p-2 border-t border-gray-100 bg-gray-50 rounded-b-lg">
      <button class="w-full py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs font-medium transition-colors">
        Apply Global Settings
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
// Logic for handling selects can be added here
</script>