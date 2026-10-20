<script setup lang="ts">
import { useApi } from '../api/useApi'
import type { TeamOut } from '../api/types'
import LoadState from '../components/LoadState.vue'

const props = defineProps<{ slug: string }>()
const { data, error, loading } = useApi<TeamOut[]>(() => `competitions/${props.slug}/teams`)
</script>

<template>
  <LoadState
    :loading="loading"
    :error="error"
  >
    <ul class="cards">
      <li
        v-for="team in data"
        :key="team.id"
      >
        <RouterLink :to="{ name: 'roster', params: { slug, teamId: team.id } }">
          {{ team.name }}
        </RouterLink>
      </li>
    </ul>
  </LoadState>
</template>
