/* xcheck driver: headless PacMan genetic-AI training, fixed seed, tunable
 * scale. Real third-party game logic (maze, ghosts, GP evolution) from
 * kcy1019/pacman, run deterministically. */
#define __TRAINER__
#include"simple.genetic.hxx"
#include<cstdio>
#include<cstdlib>
int main(int argc, char **argv)
{
    int gens = argc > 1 ? atoi(argv[1]) : 6;
    int pop  = argc > 2 ? atoi(argv[2]) : 60;
    PacManTrainer trainer(200000, gens, pop, 0.05, 0.75, 3, "apps/game1.dat");
    auto&& res = trainer.Train();
    res[0].ExportWeights("/tmp/xg1.dat");        /* checksum via exported genes */
    res[1].ExportWeights("/tmp/xg2.dat");
    printf("pacman gens=%d pop=%d done genes=%zu\n", gens, pop, res.size());
    return 0;
}
