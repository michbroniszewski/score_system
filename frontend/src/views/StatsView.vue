<script setup lang="ts">
import { computed } from 'vue'
import { statLabel } from '../api/format'
import { useApi } from '../api/useApi'
import type { PlayerStatsOut } from '../api/types'
import LoadState from '../components/LoadState.vue'

const props = defineProps<{ slug: string }>()
const { data, error, loading } = useApi<PlayerStatsOut[]>(
  () => `competitions/${props.slug}/stats`,
)
// Every row has the same statistics (those of the preset), in the preset's order.
const columns = computed(() => Object.keys(data.value?.[0]?.stats ?? {}))
</script>

<template>
  <LoadState
    :loading="loading"
    :error="error"
  >
    <div
      v-if="data?.length"
      class="table-wrap"
    >
      <table>
        <thead>
          <tr>
            <th class="left">
              Zawodnik
            </th>
            <th class="left">
              Drużyna
            </th>
            <th
              v-for="code in columns"
              :key="code"
            >
              {{ statLabel(code) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in data"
            :key="row.player.id"
          >
            <td class="left">
              {{ row.player.name }}
            </td>
            <td class="left">
              {{ row.team?.name ?? '' }}
            </td>
            <td
              v-for="code in columns"
              :key="code"
            >
              {{ row.stats[code] }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p
      v-else
      class="notice"
    >
      Brak statystyk.
    </p>
  </LoadState>
</template>
