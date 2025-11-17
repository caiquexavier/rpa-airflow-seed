<template>
  <component :is="iconComponent" :class="iconClass" />
</template>

<script setup lang="ts">
import { computed, h } from 'vue';

const props = defineProps<{
  icon?: string;
  service?: string;
  category?: string;
  size?: number;
}>();

const iconSize = computed(() => props.size || 24);

const iconComponent = computed(() => {
  // Auto-detect Airflow icon for Airflow service if no icon specified
  if (props.service === 'airflow' && !props.icon) {
    return () => getAirflowIcon(iconSize.value);
  }
  
  // Determine which icon to show based on icon prop, service, or category
  const iconName = props.icon || getIconFromService(props.service) || getIconFromCategory(props.category);
  
  return () => getIconSVG(iconName, iconSize.value);
});

const iconClass = computed(() => 'node-icon-svg');

function getIconFromService(service?: string): string | null {
  if (!service) return null;
  const serviceMap: Record<string, string> = {
    'airflow': 'airflow',
    'rpa-api': 'api',
    'rpa-listener': 'rabbitmq',
    'rpa-robots': 'robot-framework',
  };
  return serviceMap[service] || null;
}

function getIconFromCategory(category?: string): string | null {
  if (!category) return null;
  const categoryMap: Record<string, string> = {
    'data-input': 'file',
    'integration': 'integration',
    'api': 'api',
    'messaging': 'rabbitmq',
    'robot': 'robot-framework',
    'storage': 's3',
    'webhook': 'webhook',
    'callback': 'callback',
  };
  return categoryMap[category] || 'task';
}

function getIconSVG(iconName: string | null, size: number) {
  if (!iconName) {
    return h('svg', {
      width: size,
      height: size,
      viewBox: '0 0 24 24',
      fill: 'none',
      class: 'default-icon'
    }, [
      h('rect', { x: '4', y: '4', width: '16', height: '16', rx: '2', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' }),
      h('path', { d: 'M9 12L11 14L15 10', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round' })
    ]);
  }

  const icons: Record<string, () => any> = {
    'airflow': () => getAirflowIcon(size),
    'robot-framework': () => getRobotFrameworkIcon(size),
    'api': () => getAPIIcon(size),
    'rabbitmq': () => getRabbitMQIcon(size),
    'webhook': () => getWebhookIcon(size),
    's3': () => getS3Icon(size),
    'file': () => getFileIcon(size),
    'integration': () => getIntegrationIcon(size),
    'callback': () => getCallbackIcon(size),
    'task': () => getTaskIcon(size),
  };

  return icons[iconName]?.() || icons['task']();
}

// Airflow Icon
function getAirflowIcon(size: number) {
  return h('svg', {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    xmlns: 'http://www.w3.org/2000/svg'
  }, [
    h('path', {
      d: 'M12 2L2 7L12 12L22 7L12 2Z',
      fill: '#E43921',
      stroke: '#E43921',
      'stroke-width': '0.5'
    }),
    h('path', {
      d: 'M2 12L12 17L22 12',
      stroke: '#E43921',
      'stroke-width': '2',
      fill: 'none'
    }),
    h('path', {
      d: 'M2 17L12 22L22 17',
      stroke: '#E43921',
      'stroke-width': '2',
      fill: 'none'
    })
  ]);
}

// Robot Framework Icon
function getRobotFrameworkIcon(size: number) {
  return h('svg', {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    xmlns: 'http://www.w3.org/2000/svg'
  }, [
    h('rect', { x: '4', y: '6', width: '16', height: '12', rx: '2', fill: '#00C0B5', stroke: '#00C0B5', 'stroke-width': '1.5' }),
    h('circle', { cx: '8', cy: '11', r: '1.5', fill: '#FFFFFF' }),
    h('circle', { cx: '16', cy: '11', r: '1.5', fill: '#FFFFFF' }),
    h('rect', { x: '9', y: '14', width: '6', height: '2', rx: '1', fill: '#FFFFFF' }),
    h('path', { d: 'M6 4L6 6', stroke: '#00C0B5', 'stroke-width': '2', 'stroke-linecap': 'round' }),
    h('path', { d: 'M18 4L18 6', stroke: '#00C0B5', 'stroke-width': '2', 'stroke-linecap': 'round' })
  ]);
}

// API Icon
function getAPIIcon(size: number) {
  return h('svg', {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    xmlns: 'http://www.w3.org/2000/svg'
  }, [
    h('rect', { x: '3', y: '5', width: '18', height: '14', rx: '2', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' }),
    h('path', { d: 'M8 9H16M8 12H16M8 15H13', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round' }),
    h('circle', { cx: '17', cy: '9', r: '1', fill: 'currentColor' })
  ]);
}

// RabbitMQ Icon
function getRabbitMQIcon(size: number) {
  return h('svg', {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    xmlns: 'http://www.w3.org/2000/svg'
  }, [
    h('circle', { cx: '8', cy: '8', r: '3', fill: '#FF6600', stroke: '#FF6600', 'stroke-width': '1.5' }),
    h('circle', { cx: '16', cy: '8', r: '3', fill: '#FF6600', stroke: '#FF6600', 'stroke-width': '1.5' }),
    h('path', { d: 'M11 8L13 8', stroke: '#FF6600', 'stroke-width': '2', 'stroke-linecap': 'round' }),
    h('path', { d: 'M8 11L8 16L16 16L16 11', stroke: '#FF6600', 'stroke-width': '2', fill: 'none', 'stroke-linecap': 'round' })
  ]);
}

// Webhook Icon
function getWebhookIcon(size: number) {
  return h('svg', {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    xmlns: 'http://www.w3.org/2000/svg'
  }, [
    h('path', { d: 'M12 2L2 7L12 12L22 7L12 2Z', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' }),
    h('path', { d: 'M2 17L12 22L22 17', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' }),
    h('path', { d: 'M2 12L12 17L22 12', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' })
  ]);
}

// S3 Icon
function getS3Icon(size: number) {
  return h('svg', {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    xmlns: 'http://www.w3.org/2000/svg'
  }, [
    h('path', { d: 'M3 6L12 2L21 6V18L12 22L3 18V6Z', stroke: '#FF9900', 'stroke-width': '2', fill: 'none' }),
    h('path', { d: 'M3 6L12 10L21 6', stroke: '#FF9900', 'stroke-width': '2', fill: 'none' }),
    h('path', { d: 'M12 10V22', stroke: '#FF9900', 'stroke-width': '2' })
  ]);
}

// File Icon
function getFileIcon(size: number) {
  return h('svg', {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    xmlns: 'http://www.w3.org/2000/svg'
  }, [
    h('path', { d: 'M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' }),
    h('path', { d: 'M14 2V8H20', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }),
    h('path', { d: 'M8 13H16M8 17H16', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round' })
  ]);
}

// Integration Icon
function getIntegrationIcon(size: number) {
  return h('svg', {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    xmlns: 'http://www.w3.org/2000/svg'
  }, [
    h('circle', { cx: '6', cy: '6', r: '3', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' }),
    h('circle', { cx: '18', cy: '6', r: '3', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' }),
    h('circle', { cx: '6', cy: '18', r: '3', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' }),
    h('circle', { cx: '18', cy: '18', r: '3', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' }),
    h('path', { d: 'M9 6L15 6M9 18L15 18M6 9L6 15M18 9L18 15', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round' })
  ]);
}

// Callback Icon
function getCallbackIcon(size: number) {
  return h('svg', {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    xmlns: 'http://www.w3.org/2000/svg'
  }, [
    h('path', { d: 'M3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12Z', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' }),
    h('path', { d: 'M8 12L11 15L16 9', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })
  ]);
}

// Task Icon (default)
function getTaskIcon(size: number) {
  return h('svg', {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    xmlns: 'http://www.w3.org/2000/svg'
  }, [
    h('rect', { x: '4', y: '4', width: '16', height: '16', rx: '2', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' }),
    h('path', { d: 'M9 12L11 14L15 10', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round' })
  ]);
}
</script>

<style scoped>
.node-icon-svg {
  color: currentColor;
  flex-shrink: 0;
}

.default-icon {
  color: #0ea5e9;
}
</style>

