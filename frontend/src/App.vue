<script setup lang="ts">
import { staticData } from './api/client'
</script>

<template>
  <header class="site-header">
    <RouterLink
      to="/"
      class="brand"
    >
      Score System
    </RouterLink>
    <RouterLink
      v-if="!staticData"
      :to="{ name: 'admin' }"
      class="admin-link"
    >
      Panel
    </RouterLink>
  </header>
  <main class="page">
    <RouterView />
  </main>
</template>
