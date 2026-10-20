<script setup lang="ts">
import { provide } from 'vue'
import { useApi } from '../api/useApi'
import type { CompetitionOut } from '../api/types'
import LoadState from '../components/LoadState.vue'
import { COMPETITION } from './competition'

const props = defineProps<{ slug: string }>()
const { data, error, loading } = useApi<CompetitionOut>(() => `competitions/${props.slug}`)
provide(COMPETITION, data)

const tabs = [
  { name: 'standings', label: 'Tabela' },
  { name: 'matches', label: 'Terminarz' },
  { name: 'teams', label: 'Drużyny' },
  { name: 'stats', label: 'Statystyki' },
]
</script>

<template>
  <LoadState
    :loading="loading"
    :error="error"
  >
    <h1>{{ data?.name }}</h1>
    <nav class="tabs">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.name"
        :to="{ name: tab.name, params: { slug } }"
      >
        {{ tab.label }}
      </RouterLink>
    </nav>
    <RouterView />
  </LoadState>
</template>
