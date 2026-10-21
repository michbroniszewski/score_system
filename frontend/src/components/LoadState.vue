<script setup lang="ts">
defineProps<{ loading: boolean; error: Error | null }>()
</script>

<template>
  <p
    v-if="error"
    class="notice error"
  >
    Nie udało się wczytać danych.
  </p>
  <p
    v-else-if="loading"
    class="notice"
  >
    Wczytywanie…
  </p>
  <slot v-else />
</template>
