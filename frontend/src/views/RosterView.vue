<script setup lang="ts">
import { computed } from 'vue'
import { useApi } from '../api/useApi'
import type { RosterEntryOut, TeamOut } from '../api/types'
import LoadState from '../components/LoadState.vue'

const props = defineProps<{ slug: string; teamId: string }>()
const teams = useApi<TeamOut[]>(() => `competitions/${props.slug}/teams`)
const roster = useApi<RosterEntryOut[]>(
  () => `competitions/${props.slug}/teams/${props.teamId}/roster`,
)

const team = computed(() => teams.data.value?.find((t) => t.id === props.teamId))
// Current players first; past entries (with left_on) are the roster history.
const current = computed(() => roster.data.value?.filter((e) => e.left_on === null) ?? [])
const past = computed(() => roster.data.value?.filter((e) => e.left_on !== null) ?? [])
</script>

<template>
  <LoadState
    :loading="roster.loading.value"
    :error="roster.error.value"
  >
    <h2>{{ team?.name }}</h2>
    <div
      v-if="current.length"
      class="table-wrap"
    >
      <table>
        <thead>
          <tr>
            <th>Nr</th>
            <th class="left">
              Zawodnik
            </th>
            <th class="left">
              Pozycja
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="entry in current"
            :key="entry.id"
          >
            <td>{{ entry.number ?? '' }}</td>
            <td class="left">
              {{ entry.player.first_name }} {{ entry.player.last_name }}
            </td>
            <td class="left">
              {{ entry.position ?? '' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p
      v-else
      class="notice"
    >
      Brak zawodników w składzie.
    </p>
    <template v-if="past.length">
      <h3>Byli zawodnicy</h3>
      <ul>
        <li
          v-for="entry in past"
          :key="entry.id"
        >
          {{ entry.player.first_name }} {{ entry.player.last_name }} (do {{ entry.left_on }})
        </li>
      </ul>
    </template>
  </LoadState>
</template>
