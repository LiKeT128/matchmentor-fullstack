import React, { useState } from 'react';
import styles from './HeroSelectionModal.module.css';
import { api } from '../services/api';

interface Hero {
    player_id: number;
    hero_name: string;
    hero_display_name: string;
    team: "radiant" | "dire";
    position: string;
    player_name?: string;
    steam_id?: string;
}

interface HeroSelectionModalProps {
    match_id: string;
    heroes: Hero[];
    onHeroSelected: (heroData: any) => void;
    loading?: boolean;
}

export const HeroSelectionModal: React.FC<HeroSelectionModalProps> = ({
    match_id,
    heroes,
    onHeroSelected,
    loading = false
}) => {
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Sort heroes to ensure Radiant/Dire split is correct even if api returns unsorted
    const radiantHeroes = heroes.filter(h => h.team === "radiant");
    const direHeroes = heroes.filter(h => h.team === "dire");

    const handleHeroClick = async (heroName: string) => {
        setIsSubmitting(true);
        try {
            const { data } = await api.post(`/api/matches/${match_id}/select-hero`, {
                hero_name: heroName
            });
            onHeroSelected(data);
        } catch (error) {
            console.error('Hero selection failed:', error);
            alert(`Error: ${error instanceof Error ? error.message : 'Failed to select hero'}`);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className={styles.overlay}>
            <div className={styles.modal}>
                <h2>Which hero did you play?</h2>
                <p className={styles.subtitle}>Select your hero to see detailed statistics</p>

                <div className={styles.teamsContainer}>
                    {/* RADIANT TEAM */}
                    <div className={styles.teamColumn}>
                        <h3 className={styles.radiant}>☀️ RADIANT</h3>
                        <div className={styles.heroList}>
                            {radiantHeroes.map(hero => {
                                let heroShortName = hero.hero_name.replace('npc_dota_hero_', '');
                                // Manual fixes for specific heroes
                                if (heroShortName === 'rattletrap') heroShortName = 'clockwerk';
                                if (heroShortName === 'furion') heroShortName = 'natures_prophet'; // or furion if supported
                                if (heroShortName === 'necrolyte') heroShortName = 'necrophos';
                                if (heroShortName === 'windrunner') heroShortName = 'windranger';
                                if (heroShortName === 'obsidian_destroyer') heroShortName = 'outworld_destroyer';
                                if (heroShortName === 'shredder') heroShortName = 'timbersaw';
                                if (heroShortName === 'doom_bringer') heroShortName = 'doom';
                                if (heroShortName === 'nevermore') heroShortName = 'shadow_fiend';
                                if (heroShortName === 'skeleton_king') heroShortName = 'wraith_king';
                                if (heroShortName === 'magnataur') heroShortName = 'magnus';
                                if (heroShortName === 'wisp') heroShortName = 'io';
                                if (heroShortName === 'centaur') heroShortName = 'centaur'; // usually correct

                                return (
                                    <button
                                        key={hero.player_id}
                                        className={styles.heroButton}
                                        onClick={() => handleHeroClick(hero.hero_name)}
                                        disabled={isSubmitting || loading}
                                        title={`${hero.hero_display_name} (${hero.position})`}
                                    >
                                        <img
                                            src={`https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/${heroShortName}.png`}
                                            alt={hero.hero_display_name}
                                            className={styles.heroImage}
                                            onError={(e) => {
                                                const target = e.currentTarget;
                                                target.onerror = null;
                                                target.src = 'https://placehold.co/100x60?text=?';
                                            }}
                                        />
                                        <div className={styles.heroInfo}>
                                            <span className={styles.heroName}>
                                                {hero.hero_display_name}
                                            </span>
                                            <span className={styles.position}>
                                                {hero['player_name'] ? `${hero['player_name']} (${hero.position})` : hero.position}
                                            </span>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* DIRE TEAM */}
                    <div className={styles.teamColumn}>
                        <h3 className={styles.dire}>🔴 DIRE</h3>
                        <div className={styles.heroList}>
                            {direHeroes.map(hero => {
                                let heroShortName = hero.hero_name.replace('npc_dota_hero_', '');
                                // Manual fixes for specific heroes
                                if (heroShortName === 'rattletrap') heroShortName = 'clockwerk';
                                if (heroShortName === 'furion') heroShortName = 'natures_prophet';
                                if (heroShortName === 'necrolyte') heroShortName = 'necrophos';
                                if (heroShortName === 'windrunner') heroShortName = 'windranger';
                                if (heroShortName === 'obsidian_destroyer') heroShortName = 'outworld_destroyer';
                                if (heroShortName === 'shredder') heroShortName = 'timbersaw';
                                if (heroShortName === 'doom_bringer') heroShortName = 'doom';
                                if (heroShortName === 'nevermore') heroShortName = 'shadow_fiend';
                                if (heroShortName === 'skeleton_king') heroShortName = 'wraith_king';
                                if (heroShortName === 'magnataur') heroShortName = 'magnus';
                                if (heroShortName === 'wisp') heroShortName = 'io';

                                return (
                                    <button
                                        key={hero.player_id}
                                        className={styles.heroButton}
                                        onClick={() => handleHeroClick(hero.hero_name)}
                                        disabled={isSubmitting || loading}
                                        title={`${hero.hero_display_name} (${hero.position})`}
                                    >
                                        <img
                                            src={`https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/${heroShortName}.png`}
                                            alt={hero.hero_display_name}
                                            className={styles.heroImage}
                                            onError={(e) => {
                                                const target = e.currentTarget;
                                                target.onerror = null;
                                                target.src = 'https://placehold.co/100x60?text=?';
                                            }}
                                        />
                                        <div className={styles.heroInfo}>
                                            <span className={styles.heroName}>
                                                {hero.hero_display_name}
                                            </span>
                                            <span className={styles.position}>
                                                {hero.position}
                                            </span>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {isSubmitting && (
                    <div className={styles.loadingOverlay}>
                        <div className={styles.spinner}></div>
                        <p>Selecting hero...</p>
                    </div>
                )}
            </div>
        </div>
    );
};
