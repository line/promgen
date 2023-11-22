<script setup>
import { ref } from "vue";
import { useSilenceStore } from "../stores/silence.js";

const store = useSilenceStore();
const form = ref({});

const submit = () => {
  const body = JSON.stringify({ labels: store.labels, ...form.value });

  fetch("/proxy/v1/silences", { method: "POST", body })
    .then((response) => {
      if (response.ok) {
        location.reload();
      } else {
        return response.json();
      }
    })
    .then((result) => {
      if (result) {
        globalStore.setMessages(result.messages); // eslint-disable-line no-undef
      }
    });
};
</script>

<template>
  <form
    v-cloak
    v-if="store.formVisible"
    @submit.prevent="submit()"
  >
    <div class="panel panel-warning">
      <div class="panel-heading">
        Silence
        <a
          type="button"
          class="close"
          @click="store.hideForm()"
        >
          &times;
        </a>
      </div>

      <div class="labels panel-body">
        <ul class="list-inline">
          <li
            v-for="(value, label) in store.labels"
            :key="label"
          >
            <a
              class="label label-warning"
              @click="store.removeLabel(label)"
            >
              {{ label }}: {{ value }}
              <span
                class="glyphicon glyphicon-remove"
                aria-hidden="true"
              ></span>
            </a>
          </li>
        </ul>
      </div>

      <table class="table table-bordered table-condensed">
        <tr>
          <th>Duration</th>
          <th>Starts</th>
          <th>Ends</th>
          <th>Comment</th>
          <th>Created by</th>
        </tr>
        <tr>
          <td>
            <input
              v-model="form.duration"
              placeholder="1m/1h/etc"
              class="form-control"
            />
          </td>
          <td>
            <input
              v-model="form.startsAt"
              placeholder="2006-10-25 14:30"
              type="datetime-local"
              class="form-control"
            />
          </td>
          <td>
            <input
              v-model="form.endsAt"
              placeholder="2006-10-25 14:30"
              type="datetime-local"
              class="form-control"
            />
          </td>
          <td>
            <input
              v-model="form.comment"
              placeholder="Silenced from Promgen"
              class="form-control"
            />
          </td>
          <td>
            <input
              v-model="form.createdBy"
              placeholder="Promgen"
              class="form-control"
            />
          </td>
        </tr>
      </table>

      <div class="panel-footer">
        <button class="btn btn-warning">{{ $t("silence") }}</button>
      </div>
    </div>
  </form>
</template>
