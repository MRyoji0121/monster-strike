// --- 定数・グローバル設定 ---
const SHOT_SPEED = 700;
const SS_TURN = 12; 
const IMG_SCALE = 48 / 256; 
const FONT_FAMILY = '"Dela Gothic One", sans-serif'; 

const levels = [
    { name: "B1", enemyHp: 200000000, enemyPos: {x: 200, y: 150}, walls: [{x: 100, y: 250}, {x: 300, y: 250}], attacks: [{ interval: 3, damageRate: 0.2, count: 3 }] },
    { name: "B2", enemyHp: 500000000, enemyPos: {x: 200, y: 120}, walls: [{x: 200, y: 300}], attacks: [{ interval: 3, damageRate: 0.2, count: 3 }] },
    { name: "Final", enemyHp: 1200000000, enemyPos: {x: 200, y: 150}, walls: [{x: 50, y: 200}, {x: 350, y: 200}, {x: 200, y: 350}], attacks: [{ interval: 2, damageRate: 0.3, count: 2 }] }
];

let players = [], turnIndex = 0, isDragging = false, isMoving = false, isClearing = false, isGameOver = false;
let arrowGuide, walls, enemy, enemyHpBar, enemyHpBarShadow, friendshipBullets, uiArea, playerHpBar, playerHpBarShadow, uiIcons = [], uiSSTexts = [], turnIndicator;
let bgImage, enemyCountText, enemyMaxHp, enemyHp, maxHp = 100000, currentHp = 100000, currentLevel = 0;
let ssCharge = [SS_TURN, SS_TURN, SS_TURN, SS_TURN], isSSWaiting = false;
let resultUI = null; 

class StartScene extends Phaser.Scene {
    constructor() { super('StartScene'); }
    preload() { this.load.image('backgroundImg', 'image_3.png'); }
    create() {
        this.add.image(200, 300, 'backgroundImg');
        this.add.text(200, 200, 'MONSTER CLONE\nOVERDRIVE', { 
            fontSize: '42px', fontFamily: FONT_FAMILY, fill: '#fff', align: 'center', stroke: '#000', strokeThickness: 8 
        }).setOrigin(0.5);
        let btn = this.add.text(200, 400, 'TAP TO START', { 
            fontSize: '28px', fontFamily: FONT_FAMILY, fill: '#ffff00', stroke: '#000', strokeThickness: 4 
        }).setOrigin(0.5).setInteractive();
        btn.on('pointerdown', () => this.scene.start('MainScene'));
        this.tweens.add({ targets: btn, alpha: 0.5, duration: 800, yoyo: true, loop: -1 });
    }
}

class MainScene extends Phaser.Scene {
    constructor() { super('MainScene'); }
    preload() {
        this.load.image('playerImg', 'image_0.png'); 
        this.load.image('arrowImg', 'image_1.png');
        this.load.image('IconImg', 'image_2.png'); 
        this.load.image('backgroundImg', 'image_3.png');
        this.load.image('enemyImg', 'image_4.png'); 
        this.load.image('blockImg', 'image_5.png');
        this.load.image('bulletImg', 'image_2.png'); 
        this.load.video('explosionVideo', 'movie_0.mp4');

        // 効果音
        this.load.audio('reflectHitSE', 'reflect_hit.mp3');
        this.load.audio('pierceHitSE', 'pierce_hit.mp3');
        this.load.audio('wallHitSE', 'wall_hit.mp3');
    }

    create() {
        players = []; turnIndex = 0; isDragging = false; isMoving = false; isClearing = false; isGameOver = false;
        uiIcons = []; uiSSTexts = []; ssCharge = [SS_TURN, SS_TURN, SS_TURN, SS_TURN]; isSSWaiting = false;
        currentHp = maxHp;

        // SE生成
        this.seReflect = this.sound.add('reflectHitSE', { volume: 0.7 });
        this.sePierce  = this.sound.add('pierceHitSE',  { volume: 0.7 });
        this.seWall    = this.sound.add('wallHitSE',    { volume: 0.5 });

        bgImage = this.add.image(200, 300, 'backgroundImg').setDepth(0);
        
        // --- UI下部エリアのデザイン ---
        uiArea = this.add.rectangle(200, 555, 400, 90, 0x222222, 0.9).setDepth(5).setStrokeStyle(2, 0x666666);
        this.physics.add.existing(uiArea, true);
        
        walls = this.physics.add.staticGroup(); 
        friendshipBullets = this.physics.add.group();

        enemy = this.physics.add.sprite(200, 150, 'enemyImg').setDepth(10);
        enemy.setScale(IMG_SCALE * 2.5); 
        enemy.body.setCircle(128).setImmovable(true);
        
        enemyCountText = this.add.text(0, 0, '', { fontSize: '28px', fontFamily: FONT_FAMILY, fill: '#f00', stroke: '#fff', strokeThickness: 4 }).setDepth(30).setOrigin(0.5);
        
        // 敵HPバー（2層）
        this.add.rectangle(200, 40, 260, 12, 0x333333).setDepth(25);
        enemyHpBarShadow = this.add.rectangle(200, 40, 256, 8, 0xffffff, 0.5).setDepth(26).setOrigin(0.5);
        enemyHpBar = this.add.rectangle(200, 40, 256, 8, 0x00ff00).setDepth(27).setOrigin(0.5);
        
        // 味方HPバー（2層）
        this.add.text(35, 510, 'HP', { fontSize: '14px', fontFamily: FONT_FAMILY, fill: '#fff' }).setDepth(46).setOrigin(0.5);
        this.add.rectangle(200, 510, 300, 14, 0x333333).setDepth(45);
        playerHpBarShadow = this.add.rectangle(200, 510, 296, 10, 0xff0000, 0.5).setDepth(46);
        playerHpBar = this.add.rectangle(200, 510, 296, 10, 0x00ff00).setDepth(47);

        arrowGuide = this.add.sprite(0, 0, 'arrowImg').setVisible(false).setOrigin(0.5, 1).setDepth(40).setTint(0xffff00);

        const startPos = [{x: 80, y: 430}, {x: 160, y: 380}, {x: 240, y: 430}, {x: 320, y: 450}];
        const playerTypes = ['reflect', 'pierce', 'reflect', 'pierce'];

        for (let i = 0; i < 4; i++) {
            let p = this.physics.add.sprite(startPos[i].x, startPos[i].y, 'playerImg').setDepth(20);
            p.setScale(IMG_SCALE); 
            p.body.setCircle(128).setCollideWorldBounds(true).setBounce(1).setDrag(0.6).setDamping(true);
            p.playerType = playerTypes[i];
            p.isHitInterval = false;
            p.hasFiredCombo = false; p.isSSPhase = 0; p.wallBounceCount = 0;
            if (p.playerType === 'pierce') p.setTint(0x8888ff);
            p.orderLabel = this.add.text(p.x, p.y - 30, (i+1) + (p.playerType === 'pierce' ? "P" : "R"), { fontSize: '10px', fontFamily: FONT_FAMILY, fill: '#fff', stroke: '#000', strokeThickness: 2 }).setOrigin(0.5).setDepth(21);
            players.push(p);

            // 衝突設定
            this.physics.add.collider(p, walls, () => {
                if (isMoving && !isClearing && !isGameOver) {
                    this.seWall.play();
                }
            });
            this.physics.add.collider(p, enemy, (pObj, eObj) => onEnemyHit(this, pObj, eObj), (pObj) => pObj.playerType === 'reflect' && pObj.isSSPhase !== 2, this);
            this.physics.add.overlap(p, enemy, (pObj, eObj) => (pObj.playerType === 'pierce' || pObj.isSSPhase === 2) && onEnemyHit(this, pObj, eObj));
            this.physics.add.collider(p, uiArea);
            this.physics.add.overlap(p, players, (p1, p2) => onPlayerHit(this, p1, p2), (p1, p2) => p1 !== p2 && !p2.hasFiredCombo && isMoving, this);

            // アイコンUI作成
            let iconX = 55 + (i * 95);
            this.add.circle(iconX, 555, 38, 0x444444).setDepth(49).setStrokeStyle(2, 0xffffff);
            let icon = this.add.image(iconX, 555, 'IconImg').setScale(IMG_SCALE * 3.5).setDepth(50).setInteractive();
            icon.on('pointerdown', () => { 
                if (!isMoving && turnIndex === i && ssCharge[i] >= SS_TURN) { 
                    isSSWaiting = !isSSWaiting; icon.setTint(isSSWaiting ? 0xff0000 : 0xffffff); 
                } 
            });
            uiIcons.push(icon);

            let ssText = this.add.text(iconX, 585, '', { fontSize: '16px', fontFamily: FONT_FAMILY, fill: '#fff', stroke: '#000', strokeThickness: 4 }).setOrigin(0.5).setDepth(55);
            uiSSTexts.push(ssText);
        }

        turnIndicator = this.add.circle(55, 555, 42).setDepth(48).setStrokeStyle(4, 0xffff00).setAlpha(0.8);
        this.tweens.add({ targets: turnIndicator, scale: 1.1, alpha: 0.4, duration: 600, yoyo: true, loop: -1 });

        this.physics.add.overlap(friendshipBullets, enemy, (e, b) => onBulletHit(this, e, b), null, this);
        initLevel(this); 
        setupControls(this);
    }
}
    update() 
        players.forEach(p => p.orderLabel.setPosition(p.x, p.y - 30));
        
        // ターンインジケーターの移動
        turnIndicator.setPosition(55 + (turnIndex * 95), 555);

        ssCharge.forEach((charge, i) => {
            if (charge >= SS_TURN) { 
                uiSSTexts[i].setText('OK').setFill('#ffff00'); 
                uiIcons[i].setAlpha(1);
            } else { 
                uiSSTexts[i].setText(SS_TURN - charge).setFill('#fff'); 
                uiIcons[i].setAlpha(0.6);
            }
        });

        if (isMoving && !isClearing && !isGameOver && players[turnIndex].body.speed < 30 && players[turnIndex].isSSPhase !== 1) {
            players[turnIndex].body.setVelocity(0, 0); 
            isMoving = false;

            if (enemyHp <= 0) { 
                startClearSequence(this); 
            } else {
                processEnemyTurn(this);
                if (currentHp <= 0) { 
                    startGameOverSequence(this); 
                } else {
                    isSSWaiting = false; 
                    uiIcons[turnIndex].clearTint();
                    turnIndex = (turnIndex + 1) % 4;
                    players.forEach(p => { 
                        p.hasFiredCombo = false; 
                        p.isSSPhase = 0; 
                        p.wallBounceCount = 0; 
                        p.clearTint(); 
                        if (p.playerType === 'pierce') p.setTint(0x8888ff); 
                    });
                }
            }
        }
        enemyCountText.setPosition(enemy.x, enemy.y - 80);

// --- システム関数 ---

function updateEnemyHpBar() {
    let ratio = Math.max(0, enemyHp / enemyMaxHp);
    enemyHpBar.displayWidth = 256 * ratio;
    enemyHpBar.scene.tweens.add({ targets: enemyHpBarShadow, displayWidth: 256 * ratio, duration: 500 });
    
    if (ratio > 0.7) enemyHpBar.fillColor = 0x00ff00;
    else if (ratio > 0.3) enemyHpBar.fillColor = 0xffff00;
    else enemyHpBar.fillColor = 0xff0000;
}

function updatePlayerHpBar() {
    let ratio = Math.max(0, currentHp / maxHp);
    playerHpBar.displayWidth = 296 * ratio;
    playerHpBar.scene.tweens.add({ targets: playerHpBarShadow, displayWidth: 296 * ratio, duration: 500 });
}

function onEnemyHit(scene, player, enemySprite) {
    if (enemyHp <= 0 || isGameOver || player.body.speed < 30) return;
    if (player.playerType === 'pierce' && player.isHitInterval) return;

    // タイプ別SE
    if (player.playerType === 'reflect') {
        scene.seReflect.play();
    } else if (player.playerType === 'pierce') {
        scene.sePierce.play();
    }

    if (isSSWaiting && player.isSSPhase === 0) {
        showSSCutin(scene); 
        isSSWaiting = false; 
        player.isSSPhase = 1; 
        player.body.setVelocity(0, 0);

        let timer = scene.time.addEvent({ 
            delay: 100, 
            repeat: 19, 
            callback: () => {
                let d = 8000000 + Phaser.Math.Between(0, 2000000); 
                enemyHp -= d; 
                showDamageText(scene, enemySprite.x, enemySprite.y, d);
                updateEnemyHpBar(); 
                enemySprite.x += (Math.random() - 0.5) * 10;
                if (timer.repeatCount === 0) startSSChase(scene, player);
            }
        });
        return;
    }

    let d = 2000000; 
    if (player.isSSPhase === 2) d = 5000000 * (1 + player.wallBounceCount * 0.8);
    enemyHp -= d + Phaser.Math.Between(0, 500000);
    showDamageText(scene, enemySprite.x, enemySprite.y, d);
    updateEnemyHpBar();

    if (player.playerType === 'pierce') {
        player.body.velocity.x *= 0.8; 
        player.body.velocity.y *= 0.8;
        player.isHitInterval = true;
        scene.time.delayedCall(150, () => { player.isHitInterval = false; });
    }

    if (enemyHp <= 0) startClearSequence(scene);
}

function processEnemyTurn(scene) {
    let dr = 0;
    levels[currentLevel].attacks.forEach(a => { 
        a.count--; 
        if (a.count <= 0) { 
            dr += a.damageRate; 
            a.count = a.interval; 
        } 
    });
    if (dr > 0) { 
        currentHp -= maxHp * dr; 
        scene.cameras.main.shake(200, 0.02); 
        updatePlayerHpBar(); 
    }
    updateEnemyCountDisplay();
}

function updateEnemyCountDisplay() { 
    enemyCountText.setText(Math.min(...levels[currentLevel].attacks.map(a => a.count))); 
}

function startSSChase(scene, player) {
    player.isSSPhase = 2; 
    player.setTint(0xff00ff);
    scene.physics.velocityFromRotation(
        Phaser.Math.Angle.Between(player.x, player.y, enemy.x, enemy.y),
        SHOT_SPEED * 1.5,
        player.body.velocity
    );
}

function showSSCutin(scene) {
    let rect = scene.add.rectangle(200, 300, 400, 120, 0x000000, 0.7).setDepth(100).setScale(0, 1);
    let txt = scene.add.text(200, 300, '流転の霊銃', { 
        fontSize: '48px', 
        fontFamily: FONT_FAMILY, 
        fill: '#fff', 
        stroke: '#ff00ff', 
        strokeThickness: 10 
    }).setOrigin(0.5).setDepth(101);

    scene.tweens.add({ targets: rect, scaleX: 1, duration: 200 });
    scene.time.delayedCall(800, () => { rect.destroy(); txt.destroy(); });
}

function onPlayerHit(scene, p1, p2) { 
    p2.hasFiredCombo = true; 
    fireHomingCombo(scene, p2); 
}

function fireHomingCombo(scene, fromP) { 
    for (let i = 0; i < 8; i++) { 
        scene.time.delayedCall(i * 100, () => { 
            if (enemyHp <= 0 || isGameOver) return;
            let b = scene.physics.add.sprite(fromP.x, fromP.y, 'bulletImg')
                .setScale(IMG_SCALE)
                .setTint(0xffff00);
            friendshipBullets.add(b); 
            scene.physics.velocityFromRotation(
                Phaser.Math.Angle.Between(b.x, b.y, enemy.x, enemy.y),
                750,
                b.body.velocity
            ); 
        }); 
    } 
}

function onBulletHit(scene, enemyObj, bulletObj) { 
    bulletObj.destroy(); 
    if (enemyHp > 0) { 
        enemyHp -= 1200000; 
        updateEnemyHpBar(); 
        if (enemyHp <= 0) startClearSequence(scene); 
    } 
}

function showDamageText(scene, x, y, damage) {
    let dmgTxt = scene.add.text(x, y, damage.toLocaleString(), { 
        fontSize: '24px', 
        fontFamily: FONT_FAMILY, 
        fill: '#ffffff', 
        stroke: '#f00', 
        strokeThickness: 6 
    }).setDepth(100).setOrigin(0.5);

    scene.tweens.add({ 
        targets: dmgTxt, 
        x: x + Phaser.Math.Between(-40, 40), 
        y: y - Phaser.Math.Between(50, 80), 
        alpha: 0, 
        duration: 800, 
        onComplete: () => dmgTxt.destroy() 
    });
}

function startGameOverSequence(scene) {
    if (isGameOver) return;
    isGameOver = true; 
    isMoving = false;
    scene.cameras.main.flash(500, 200, 0, 0);

    let goLogo = scene.add.text(200, 300, 'GAME OVER', { 
        fontSize: '60px', 
        fontFamily: FONT_FAMILY, 
        fill: '#ff0000', 
        stroke: '#000', 
        strokeThickness: 12 
    }).setOrigin(0.5).setDepth(300).setScale(2).setAlpha(0);

    scene.tweens.add({ targets: goLogo, alpha: 1, scale: 1, duration: 800, ease: 'Power2' });
    scene.time.delayedCall(1500, () => showGameOverResult(scene, goLogo));
}

function showGameOverResult(scene, logo) {
    if (resultUI) resultUI.destroy();
    resultUI = scene.add.container(0, 0).setDepth(350);

    let overlay = scene.add.rectangle(200, 300, 400, 600, 0x000000, 0.9).setAlpha(0);
    let msg = scene.add.text(200, 200, "BATTLE FAILED...", { 
        fontSize: '24px', 
        fontFamily: FONT_FAMILY, 
        fill: '#fff' 
    }).setOrigin(0.5).setAlpha(0);

    let retryBtn = scene.add.text(200, 500, 'RETRY STAGE', { 
        fontSize: '28px', 
        fontFamily: FONT_FAMILY, 
        fill: '#ffff00', 
        stroke: '#000', 
        strokeThickness: 6 
    }).setOrigin(0.5).setInteractive().setAlpha(0);

    resultUI.add([overlay, logo, msg, retryBtn]);
    scene.tweens.add({ targets: [overlay, msg, retryBtn], alpha: 1, duration: 500 });

    retryBtn.on('pointerdown', () => { 
        if (resultUI) { resultUI.destroy(); resultUI = null; } 
        currentHp = maxHp; 
        initLevel(scene); 
    });
}

function startClearSequence(scene) {
    if (isClearing) return;
    isClearing = true; 
    scene.physics.world.timeScale = 5; 
    scene.cameras.main.flash(500, 255, 255, 255);

    scene.time.delayedCall(1000, () => {
        scene.physics.world.timeScale = 1; 
        try { 
            let v = scene.add.video(enemy.x, enemy.y, 'explosionVideo').setDepth(100).setScale(2); 
            v.play(); 
            v.on('complete', () => v.destroy()); 
        } catch(e) {}

        enemy.setVisible(false); 
        enemyCountText.setVisible(false);

        let clearLogo = scene.add.text(200, -100, 'CLEAR!', { 
            fontSize: '80px', 
            fontFamily: FONT_FAMILY, 
            fill: '#ffff00', 
            stroke: '#ff6600', 
            strokeThickness: 15, 
            fontStyle: 'italic' 
        }).setOrigin(0.5).setDepth(200);

        scene.tweens.add({ 
            targets: clearLogo, 
            y: 300, 
            duration: 600, 
            ease: 'Bounce.out', 
            onComplete: () => { 
                scene.time.delayedCall(1000, () => showResultScreen(scene, clearLogo)); 
            } 
        });
    });
}

function showResultScreen(scene, logo) {
    if (resultUI) resultUI.destroy();
    resultUI = scene.add.container(0, 0).setDepth(250);

    let overlay = scene.add.rectangle(200, 300, 400, 600, 0x000000, 0.8).setAlpha(0);
    let nextBtn = scene.add.text(200, 500, 'NEXT STAGE >>', { 
        fontSize: '24px', 
        fontFamily: FONT_FAMILY, 
        fill: '#00ff00' 
    }).setOrigin(0.5).setInteractive().setAlpha(0);

    resultUI.add([overlay, logo, nextBtn]); 
    scene.tweens.add({ targets: [overlay, nextBtn], alpha: 1, duration: 500 });

    nextBtn.on('pointerdown', () => goToNextStage(scene));
}

function initLevel(scene) {
    isClearing = false; 
    isGameOver = false; 
    isMoving = false; 
    isDragging = false; 
    isSSWaiting = false;

    scene.physics.world.timeScale = 1;
    const d = levels[currentLevel]; 

    enemyHp = d.enemyHp; 
    enemyMaxHp = d.enemyHp;

    enemy.setPosition(d.enemyPos.x, d.enemyPos.y).setVisible(true).clearTint();
    enemyCountText.setVisible(true);

    walls.clear(true, true); 
    d.walls.forEach(w => { 
        let block = walls.create(w.x, w.y, 'blockImg'); 
        block.setScale(IMG_SCALE * 2).refreshBody(); 
    });

    const startPos = [{x: 80, y: 430}, {x: 160, y: 380}, {x: 240, y: 430}, {x: 320, y: 450}];
    players.forEach((p, i) => { 
        p.setPosition(startPos[i].x, startPos[i].y); 
        p.body.setVelocity(0, 0); 
        p.hasFiredCombo = false; 
        p.isSSPhase = 0; 
        p.clearTint(); 
        if (p.playerType === 'pierce') p.setTint(0x8888ff);
    });

    updateEnemyHpBar(); 
    updatePlayerHpBar(); 
    updateEnemyCountDisplay();
}

function goToNextStage(scene) { 
    if (resultUI) { resultUI.destroy(); resultUI = null; }
    currentLevel++; 
    if (currentLevel < levels.length) { 
        initLevel(scene); 
    } else { 
        alert("ALL CLEAR!"); 
        location.reload(); 
    } 
}

function setupControls(scene) {
    scene.input.on('pointerdown', p => { 
        if (!isMoving && !isClearing && !isGameOver &&
            Phaser.Math.Distance.Between(p.x, p.y, players[turnIndex].x, players[turnIndex].y) < 40) { 
            isDragging = true; 
            arrowGuide.setVisible(true); 
        } 
    });

    scene.input.on('pointermove', p => { 
        if (isDragging) {
            arrowGuide
                .setPosition(players[turnIndex].x, players[turnIndex].y)
                .setRotation(
                    Phaser.Math.Angle.Between(p.x, p.y, p.downX, p.downY) + Math.PI / 2
                ); 
        }
    });

    scene.input.on('pointerup', p => { 
        if (!isDragging) return; 
        isDragging = false; 
        isMoving = true; 
        arrowGuide.setVisible(false); 

        if (isSSWaiting) ssCharge[turnIndex] = 0; 
        else ssCharge = ssCharge.map(c => Math.min(c + 1, SS_TURN)); 

        scene.physics.velocityFromRotation(
            Phaser.Math.Angle.Between(p.x, p.y, p.downX, p.downY),
            SHOT_SPEED,
            players[turnIndex].body.velocity
        ); 
    });
}

const config = { 
    type: Phaser.AUTO, 
    width: 400, 
    height: 600, 
    physics: { 
        default: 'arcade', 
        arcade: { gravity: { y: 0 } } 
    }, 
    scene: [ StartScene, MainScene ] 
};

const game = new Phaser.Game(config);
