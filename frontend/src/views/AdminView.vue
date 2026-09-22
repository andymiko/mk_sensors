<script setup>
import { onMounted, ref } from "vue";
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import MultiSelect from "primevue/multiselect";
import Tab from "primevue/tab";
import TabList from "primevue/tablist";
import TabPanel from "primevue/tabpanel";
import TabPanels from "primevue/tabpanels";
import Tabs from "primevue/tabs";
import Tag from "primevue/tag";
import ToggleSwitch from "primevue/toggleswitch";
import { useAdminStore } from "../stores/admin";

const admin = useAdminStore();
const dialog = ref(null);
const form = ref({ code: "", name: "", description: "" });
function open(type) {
  dialog.value = type;
  form.value = { code: "", name: "", description: "" };
}
async function create() {
  if (dialog.value === "role") await admin.createRole(form.value);
  else await admin.createPermission(form.value);
  dialog.value = null;
}
onMounted(() => admin.loadAll());
</script>

<template>
  <section class="page-stack">
    <div class="page-title">
      <span class="eyebrow">УПРАВЛЕНИЕ</span>
      <h1>Администрирование</h1>
      <p>Пользователи, роли, разрешения и все файлы системы.</p>
    </div>
    <Tabs value="users" class="section-card admin-tabs"
      ><TabList
        ><Tab value="users">Пользователи</Tab><Tab value="roles">Роли</Tab
        ><Tab value="permissions">Разрешения</Tab
        ><Tab value="files">Файлы</Tab></TabList
      ><TabPanels>
        <TabPanel value="users"
          ><DataTable
            :value="admin.users"
            :loading="admin.loading"
            responsive-layout="scroll"
            ><Column field="name" header="ФИО" /><Column
              field="email"
              header="Email" /><Column header="Роли"
              ><template #body="{ data }"
                ><div class="tag-wrap">
                  <Tag
                    v-for="role in data.roles"
                    :key="role.id"
                    :value="role.name"
                  /></div></template></Column
            ><Column header="Активен"
              ><template #body="{ data }"
                ><ToggleSwitch
                  :model-value="data.is_active"
                  @update:model-value="
                    admin.setUserStatus(data, $event)
                  " /></template></Column
            ><Column header="Назначить роли"
              ><template #body="{ data }"
                ><MultiSelect
                  :model-value="data.roles.map((role) => role.id)"
                  :options="admin.roles"
                  option-label="name"
                  option-value="id"
                  display="chip"
                  @update:model-value="
                    admin.setUserRoles(data, $event)
                  " /></template></Column></DataTable
        ></TabPanel>
        <TabPanel value="roles"
          ><div class="section-heading-inline">
            <h2>Роли</h2>
            <Button label="Создать" icon="pi pi-plus" @click="open('role')" />
          </div>
          <DataTable :value="admin.roles"
            ><Column field="name" header="Название" /><Column
              field="code"
              header="Код" /><Column header="Разрешения"
              ><template #body="{ data }"
                ><MultiSelect
                  :model-value="data.permissions.map((item) => item.id)"
                  :options="admin.permissions"
                  option-label="name"
                  option-value="id"
                  display="chip"
                  @update:model-value="
                    admin.setRolePermissions(data, $event)
                  " /></template></Column></DataTable
        ></TabPanel>
        <TabPanel value="permissions"
          ><div class="section-heading-inline">
            <h2>Разрешения</h2>
            <Button
              label="Создать"
              icon="pi pi-plus"
              @click="open('permission')"
            />
          </div>
          <DataTable :value="admin.permissions"
            ><Column field="name" header="Название" /><Column
              field="code"
              header="Код" /><Column
              field="description"
              header="Описание" /></DataTable
        ></TabPanel>
        <TabPanel value="files"
          ><DataTable :value="admin.files"
            ><Column field="original_name" header="Файл" /><Column
              field="user_id"
              header="Пользователь"
            /><Column field="content_type" header="Тип" /><Column header="Дата"
              ><template #body="{ data }">{{
                new Date(data.created_at * 1000).toLocaleString("ru-RU")
              }}</template></Column
            ></DataTable
          ></TabPanel
        >
      </TabPanels></Tabs
    >
    <Dialog
      v-model:visible="dialog"
      modal
      :header="dialog === 'role' ? 'Новая роль' : 'Новое разрешение'"
      class="editor-dialog"
      ><div class="form-stack">
        <label>Код<InputText v-model="form.code" /></label
        ><label>Название<InputText v-model="form.name" /></label
        ><label>Описание<InputText v-model="form.description" /></label
        ><Button
          label="Создать"
          :disabled="!form.code || !form.name"
          @click="create"
        /></div
    ></Dialog>
  </section>
</template>
