<script setup lang="ts">
import { useApi } from '../api/useApi'
import type { CompetitionOut } from '../api/types'
import LoadState from '../components/LoadState.vue'

const { data, error, loading } = useApi<CompetitionOut[]>(() => 'competitions')
</script>

<template>
  <h1>Rozgrywki</h1>
  <LoadState
    :loading="loading"
    :error="error"
  >
    <ul
      v-if="data?.length"
      class="cards"
    >
      <li
        v-for="comp in data"
        :key="comp.slug"
      >
        <RouterLink :to="{ name: 'standings', params: { slug: comp.slug } }">
          {{ comp.name }}
        </RouterLink>
      </li>
    </ul>
    <p
      v-else
      class="notice"
    >
      Brak rozgrywek.
    </p>
  </LoadState>
</template>
