<script setup lang="ts">
import { useApi } from '../api/useApi'
import type { StandingOut } from '../api/types'
import LoadState from '../components/LoadState.vue'

const props = defineProps<{ slug: string }>()
const { data, error, loading } = useApi<StandingOut[]>(
  () => `competitions/${props.slug}/standings`,
)
</script>

<template>
  <LoadState
    :loading="loading"
    :error="error"
  >
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th class="left">
              Drużyna
            </th>
            <th title="Mecze">
              M
            </th>
            <th title="Zwycięstwa">
              Z
            </th>
            <th title="Porażki">
              P
            </th>
            <th title="Punkty">
              Pkt
            </th>
            <th>Sety</th>
            <th>Małe pkt</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in data"
            :key="row.team.id"
          >
            <td>{{ row.position }}</td>
            <td class="left">
              <RouterLink :to="{ name: 'roster', params: { slug, teamId: row.team.id } }">
                {{ row.team.name }}
              </RouterLink>
            </td>
            <td>{{ row.played }}</td>
            <td>{{ row.wins }}</td>
            <td>{{ row.losses }}</td>
            <td class="strong">
              {{ row.points }}
            </td>
            <td>{{ row.sets_won }}:{{ row.sets_lost }}</td>
            <td>{{ row.small_points_won }}:{{ row.small_points_lost }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </LoadState>
</template>
