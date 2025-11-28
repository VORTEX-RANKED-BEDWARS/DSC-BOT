# VORTEX Ranked Bedwars Website

Official website for VORTEX Ranked Bedwars server - **vortexrbw.club**

## 🎮 About

This is a modern, responsive website for the VORTEX Ranked Bedwars Minecraft server. The site features:

- Responsive design that works on all devices
- Interactive statistics and leaderboards
- Modern gaming aesthetic with smooth animations
- Server information and how to join
- Mobile-friendly navigation

## 📁 Files

- `index.html` - Main website page
- `styles.css` - All styling and animations
- `script.js` - Interactive features and functionality
- `README.md` - This file

## 🚀 Deployment

### Option 1: GitHub Pages

1. Push these files to your GitHub repository
2. Go to repository Settings → Pages
3. Select the branch (main) and root folder
4. Save and your site will be live at: `https://yourusername.github.io/repository-name`

### Option 2: Netlify

1. Create an account at [netlify.com](https://netlify.com)
2. Drag and drop these files or connect your GitHub repository
3. Deploy! Your site will be live instantly

### Option 3: Vercel

1. Create an account at [vercel.com](https://vercel.com)
2. Import your GitHub repository or upload files
3. Deploy with zero configuration

### Option 4: Custom Hosting

Upload all files to your web hosting via FTP:
- Make sure `index.html` is in the root directory
- Ensure all files maintain their names
- Configure your domain (vortexrbw.club) to point to your hosting

## 🔧 Customization

### Update Server IP
Edit in `index.html` and `script.js`:
```javascript
const ip = 'vortexrbw.club'; // Change to your server IP
```

### Change Colors
Edit CSS variables in `styles.css`:
```css
:root {
    --primary-color: #6366f1;
    --secondary-color: #8b5cf6;
    --accent-color: #ec4899;
}
```

### Update Statistics
Edit the hero stats in `index.html`:
```html
<div class="stat-number" data-target="1250">0</div>
```

### Modify Leaderboard
Update leaderboard entries in `index.html` under the `#leaderboard` section.

### Add Discord Link
Edit in `script.js`:
```javascript
window.open('https://discord.gg/your-invite-code', '_blank');
```

## 🎨 Features

- **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- **Smooth Animations**: Fade-in effects, parallax scrolling, and interactive elements
- **Copy Server IP**: One-click copy functionality for easy joining
- **Statistics Counter**: Animated counters for server statistics
- **Mobile Navigation**: Hamburger menu for mobile devices
- **Modern UI**: Gaming-themed design with gradient effects

## 🌐 Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers

## 📝 License

This website template is provided for VORTEX Ranked Bedwars. Feel free to customize it for your needs.

## 🔗 Links

- Server IP: **vortexrbw.club**
- Discord: [Add your Discord invite link]
- Store: [Add your store link if applicable]

## 🛠️ Technical Details

- Pure HTML, CSS, and JavaScript (no frameworks required)
- No build process needed
- Optimized for performance
- SEO-friendly structure
- Accessible design

## 📞 Support

For issues or questions about the website, contact the VORTEX development team.

---

**Not affiliated with Mojang or Microsoft.**
