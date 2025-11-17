<script setup lang="ts">
// Redirect to home page
const router = useRouter();

onMounted(() => {
  router.replace('/home');
});
</script>

<template>
  <div></div>
</template>

