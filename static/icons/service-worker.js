if (!navigator.serviceWorker.getRegistrations().then(registrations => registrations.some(registration => registration.active.scriptURL === '/service_worker.js'))) {
  navigator.serviceWorker.register('/service_worker.js', {
    scope: '/',
  });
}
