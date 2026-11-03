(() => {
  const avatars = {
    maya: {name:"Maya", role:"Curious learner", background:"#f0dfff", skin:"#a85d45", hair:"#30213d", shirt:"#7956d8", style:"bob"},
    ari: {name:"Ari", role:"Chart explorer", background:"#d9efff", skin:"#e7b68d", hair:"#523521", shirt:"#3d77b8", style:"short"},
    candela: {name:"Candela", role:"Friendly mentor", background:"#ffefd1", skin:"#d99a68", hair:"#653d31", shirt:"#c77849", style:"curly", glasses:true},
    leo: {name:"Leo", role:"Steady beginner", background:"#ddf3e8", skin:"#704331", hair:"#201d26", shirt:"#408871", style:"short"},
    nia: {name:"Nia", role:"Market strategist", background:"#ffe1e7", skin:"#c98266", hair:"#312538", shirt:"#bc5277", style:"bun", glasses:true}
  };

  function avatarMarkup(id, className = "avatar-art") {
    const avatar = avatars[id] || avatars.candela;
    let hairBack = "";
    let hairFront = "<path d=\"M30 39c-3-17 6-29 21-29 15 0 23 11 20 29-7-3-13-9-17-17-5 8-13 14-24 17z\" fill=\"{hair}\"/>";
    if (avatar.style === "bob") {
      hairBack = "<path d=\"M29 43c-4-20 7-33 22-33 17 0 26 14 21 38l-5 21-7-2 2-21H38l2 23-8 1-5-27z\" fill=\"{hair}\"/>";
      hairFront = "<path d=\"M29 39c-2-19 7-29 22-29 16 0 23 11 21 28-9-3-15-10-19-18-5 9-13 15-24 19z\" fill=\"{hair}\"/>";
    }
    if (avatar.style === "curly") {
      hairBack = "<path d=\"M29 45c-4-20 5-35 22-35 18 0 25 15 21 37l-5 18-8-3 3-20H38l2 22-8 1-4-20z\" fill=\"{hair}\"/>";
      hairFront = "<g fill=\"{hair}\"><circle cx=\"32\" cy=\"29\" r=\"9\"/><circle cx=\"43\" cy=\"17\" r=\"10\"/><circle cx=\"56\" cy=\"16\" r=\"10\"/><circle cx=\"68\" cy=\"27\" r=\"9\"/><path d=\"M31 36c6-3 10-8 12-14 5 7 11 11 19 13l-1 8H32z\"/></g>";
    }
    if (avatar.style === "bun") {
      hairBack = "<circle cx=\"72\" cy=\"17\" r=\"11\" fill=\"{hair}\"/><path d=\"M29 43c-3-19 7-33 22-33 17 0 25 14 21 38l-5 19-8-2 2-21H38l2 22-8 1-4-22z\" fill=\"{hair}\"/>";
      hairFront = "<path d=\"M30 39c-2-18 7-29 21-29 16 0 23 12 21 29-8-4-15-10-18-18-5 9-13 15-24 18z\" fill=\"{hair}\"/>";
    }
    hairBack = hairBack.replaceAll("{hair}", avatar.hair);
    hairFront = hairFront.replaceAll("{hair}", avatar.hair);
    const glasses = avatar.glasses
      ? "<g fill=\"none\" stroke=\"#49352f\" stroke-width=\"2.5\"><rect x=\"36\" y=\"41\" width=\"12\" height=\"9\" rx=\"3\"/><rect x=\"52\" y=\"41\" width=\"12\" height=\"9\" rx=\"3\"/><path d=\"M48 45h4m-16 0-4-2m32 2 4-2\"/></g>"
      : "";
    return `<svg class="${className}" viewBox="0 0 100 100" role="img" aria-label="${avatar.name}, ${avatar.role}" xmlns="http://www.w3.org/2000/svg">
      <circle cx="50" cy="50" r="49" fill="${avatar.background}"/>
      <path d="M12 105c2-22 16-34 38-34s36 12 38 34" fill="${avatar.shirt}"/>
      <path d="M42 61h16v17H42z" fill="${avatar.skin}"/>
      ${hairBack}
      <ellipse cx="50" cy="45" rx="20" ry="24" fill="${avatar.skin}"/>
      ${hairFront}
      <g fill="#35252a"><circle cx="42" cy="45" r="1.8"/><circle cx="58" cy="45" r="1.8"/></g>
      ${glasses}
      <path d="M44 56c4 4 8 4 12 0" fill="none" stroke="#793e38" stroke-width="2" stroke-linecap="round"/>
      <path d="M37 38c3-2 6-2 9-1m8 0c3-1 6-1 9 1" fill="none" stroke="${avatar.hair}" stroke-width="2" stroke-linecap="round"/>
      <path d="M16 91c7-9 18-14 34-14s27 5 34 14" fill="none" stroke="#ffffff" stroke-opacity=".42" stroke-width="3"/>
    </svg>`;
  }

  window.TRADO_AVATARS = avatars;
  window.tradoAvatarMarkup = avatarMarkup;
})();
