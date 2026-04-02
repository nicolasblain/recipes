(function() {
  var items = document.querySelectorAll('.recipe-item');
  var searchInput = document.getElementById('search');
  var tabsContainer = document.getElementById('tabs');
  var noResults = document.getElementById('noResults');
  var searchCount = document.getElementById('searchCount');
  var activeTag = null;

  // Collect unique tags in document order
  var tagOrder = [];
  var tagSet = {};
  items.forEach(function(item) {
    var tag = item.getAttribute('data-tags') || '';
    if (tag && !tagSet[tag]) {
      tagSet[tag] = true;
      tagOrder.push(tag);
    }
  });

  // Build tag buttons
  var allTab = document.createElement('button');
  allTab.className = 'tab active';
  allTab.textContent = 'All';
  allTab.setAttribute('data-tag', '');
  tabsContainer.appendChild(allTab);
  activeTag = allTab;

  tagOrder.forEach(function(tag) {
    var btn = document.createElement('button');
    btn.className = 'tab';
    btn.textContent = tag;
    btn.setAttribute('data-tag', tag);
    tabsContainer.appendChild(btn);
  });

  var tabs = tabsContainer.querySelectorAll('.tab');

  tabs.forEach(function(tab) {
    tab.addEventListener('click', function() {
      activeTag.classList.remove('active');
      tab.classList.add('active');
      activeTag = tab;
      applyFilters();
    });
  });

  function normalize(str) {
    return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  searchInput.addEventListener('input', function() {
    applyFilters();
  });

  function applyFilters() {
    var query = normalize(searchInput.value.trim());
    var targetTag = activeTag.getAttribute('data-tag');
    var visibleCount = 0;

    items.forEach(function(item) {
      var name = normalize(item.getAttribute('data-name') || '');
      var text = normalize(item.textContent || '');
      var itemTag = item.getAttribute('data-tags') || '';
      var matchesTag = !targetTag || itemTag === targetTag;
      var matchesSearch = !query || name.indexOf(query) !== -1 || text.indexOf(query) !== -1;

      if (matchesTag && matchesSearch) {
        item.classList.remove('hidden');
        visibleCount++;
      } else {
        item.classList.add('hidden');
      }
    });

    if (query) {
      searchCount.style.display = 'block';
      searchCount.textContent = visibleCount + ' recipe' + (visibleCount !== 1 ? 's' : '') + ' found';
      noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    } else {
      searchCount.style.display = 'none';
      noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    }
  }
})();

// Recipe detail overlay with markdown rendering
(function() {
  var overlay = document.getElementById('recipeOverlay');
  var body = document.getElementById('recipeBody');
  var closeBtn = document.getElementById('recipeClose');
  var backBtn = document.getElementById('recipeBack');

  function closeOverlay() {
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  closeBtn.addEventListener('click', closeOverlay);
  backBtn.addEventListener('click', closeOverlay);
  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) closeOverlay();
  });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeOverlay();
  });

  function stripFrontmatter(md) {
    return md.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/, '');
  }

  function parseFrontmatter(md) {
    var match = md.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    if (!match) return {};
    var data = {};
    match[1].split('\n').forEach(function(line) {
      var kv = line.match(/^(\w[\w_]*):\s*(.*)/);
      if (!kv) return;
      var val = kv[2].trim().replace(/^["']|["']$/g, '');
      data[kv[1]] = val;
    });
    return data;
  }

  function renderMeta(meta) {
    var parts = [];
    if (meta.prep_time) parts.push('Prep: ' + meta.prep_time);
    if (meta.cook_time) parts.push('Cook: ' + meta.cook_time);
    if (meta.servings) parts.push('Servings: ' + meta.servings);
    if (meta.source) {
      var domain = meta.source.replace(/^https?:\/\//, '').split('/')[0];
      parts.push('<a href="' + meta.source + '" target="_blank" rel="noopener">' + domain + '</a>');
    }
    if (parts.length === 0) return '';
    return '<div class="recipe-meta">' + parts.map(function(p) { return '<span>' + p + '</span>'; }).join('') + '</div>';
  }

  document.addEventListener('click', function(e) {
    var link = e.target.closest('a[href$=".md"]');
    if (!link) return;
    e.preventDefault();
    var href = link.getAttribute('href');

    body.innerHTML = '<p style="color:var(--text-muted);font-style:italic;">Loading recipe...</p>';
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
    overlay.scrollTop = 0;

    fetch(href)
      .then(function(r) {
        if (!r.ok) throw new Error('Not found');
        return r.text();
      })
      .then(function(md) {
        var meta = parseFrontmatter(md);
        var content = stripFrontmatter(md);
        body.innerHTML = renderMeta(meta) + marked.parse(content);
      })
      .catch(function() {
        body.innerHTML = '<p style="color:#c33;">Could not load recipe. The file may not be available yet.</p>';
      });
  });
})();
