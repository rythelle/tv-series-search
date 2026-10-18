<template>
  <a class="skip-link" href="#main-content">Skip to content</a>
  <header class="site-header">
    <div class="site-header__inner">
      <router-link class="brand" :to="{ name: 'search' }"><span class="brand-mark" aria-hidden="true"></span> TV Series Search</router-link>
      <span class="site-header__note">The series archive</span>
    </div>
  </header>
  <router-view />
</template>
